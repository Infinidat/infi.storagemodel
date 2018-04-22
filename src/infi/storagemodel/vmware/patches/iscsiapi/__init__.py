import infi.iscsiapi
from infi.iscsiapi import base
from infi.iscsiapi import auth as iscsiapi_auth_module
from infi.pyutils.contexts import contextmanager
from infi.pyutils.patch import monkey_patch
from infi.dtypes.iqn import IQN
from logging import getLogger


logger = getLogger(__name__)


PROPERTY_COLLECTOR_KEY = 'infi.iscsiapi'
HBAAPI_PROPERTY_PATH = 'config.storageDevice.hostBusAdapter'
SCSI_TOPOLOGY_PROPERTY_PATH = 'config.storageDevice.scsiTopology.adapter'


def install_property_collectors_on_client(client):
    from infi.pyvmomi_wrapper.property_collector import HostSystemCachedPropertyCollector
    if PROPERTY_COLLECTOR_KEY in client.property_collectors:
        return
    collector = HostSystemCachedPropertyCollector(client, [HBAAPI_PROPERTY_PATH, SCSI_TOPOLOGY_PROPERTY_PATH])
    client.property_collectors[PROPERTY_COLLECTOR_KEY] = collector


@contextmanager
def with_host(client, host):
    from infi.pyvmomi_wrapper import get_reference_to_managed_object
    monkey_patch(infi.iscsiapi, "get_iscsiapi", ConnectionManagerFactory.get)
    previous = ConnectionManagerFactory.get()
    try:
        ConnectionManagerFactory.set(ConnectionManagerFactory.create(client, host))
        yield
    finally:
        ConnectionManagerFactory.set(previous)


class ConnectionManager(base.ConnectionManager):
    def __init__(self, client, moref):
        super(ConnectionManager, self).__init__()
        self._moref = moref
        self._client = client
        self._adapter = None
        self._install_property_collector()

    def set_adapter(self, adapter):
        # accepts a string matching the 'device' attribute of a HostInternetScsiHba, e.g. "vmhba35"
        self._adapter = adapter

    def _install_property_collector(self):
        install_property_collectors_on_client(self._client)

    def _get_properties(self):
        properties = self._client.property_collectors[PROPERTY_COLLECTOR_KEY].get_properties().get(self._moref, dict())
        return properties

    def _get_all_host_bus_adapters(self):
        return self._get_properties().get(HBAAPI_PROPERTY_PATH, [])

    def _get_all_iscsi_host_bus_adapters(self):
        from pyVmomi import vim
        return [adapter for adapter in self._get_all_host_bus_adapters() if isinstance(adapter, vim.HostInternetScsiHba)]

    def _get_iscsi_host_bus_adapter(self, adapter=None):
        # the host bus adapter to retrieve can be either from parameter (specific adapter requested by caller, e.g. to
        # get IQN of specific session where adapter is known) or from 'set_adapter' (default adapter that caller wants
        # to work with - e.g. to login) or None for default behavior (use the software adapter)
        # adapter
        from pyVmomi import vim
        adapters = self._get_all_host_bus_adapters()
        to_match = adapter or self._adapter
        if to_match:
            # requested specific adapter - "to_match" is string like "vmhba33"
            adapters = [adapter for adapter in adapters if adapter.device == to_match]
        else:
            # default is "software adapter"
            adapters = [adapter for adapter in adapters if adapter.driver == 'iscsi_vmk']
        if len(adapters) == 0:
            raise RuntimeError("No matching iSCSI adatpers found on host.")
        return adapters[0]

    def _get_host_storage_system(self):
        host = self._client.get_managed_object_by_reference(self._moref)
        return host.configManager.storageSystem

    def _get_source_iqn(self, adapter=None):
        # this get_source_iqn returns a single iqn for the currently used hba
        # the external get_source_iqn returns all iqns (from all adapters), in order for 'register' to register all
        # available iqns on host
        iscsi_adapter = self._get_iscsi_host_bus_adapter(adapter)
        return IQN(iscsi_adapter.iScsiName)

    def get_source_iqn(self):
        return [IQN(iscsi_adapter.iScsiName) for iscsi_adapter in self._get_all_iscsi_host_bus_adapters()]

    def set_source_iqn(self, iqn):
        _ = IQN(iqn)   # checks iqn is valid
        self._get_host_storage_system().UpdateInternetScsiName(self._get_source_iqn(), iqn)

    def discover(self, ip_address, port=3260):
        # ugly trick: in VMware discovery and login_all happen at once, so we don't do the login here
        # and don't return a real "Target" object. Everything happens in login_all
        return (ip_address, port)

    def undiscover(self, target=None):
        # real undiscover happens with "logout_all"
        pass

    def _iscsiapi_auth_to_vmware_auth(self, iscsiapi_auth):
        from pyVmomi import vim
        if isinstance(iscsiapi_auth, iscsiapi_auth_module.ChapAuth):
            return vim.HostInternetScsiHbaAuthenticationProperties(
                chapAuthEnabled=True,
                chapAuthenticationType=vim.HostInternetScsiHbaChapAuthenticationType.chapRequired,
                chapName=iscsiapi_auth.get_inbound_username(),
                chapSecret=iscsiapi_auth.get_inbound_secret())
        if isinstance(iscsiapi_auth, iscsiapi_auth_module.MutualChapAuth):
            return vim.HostInternetScsiHbaAuthenticationProperties(
                chapAuthEnabled=True,
                chapAuthenticationType=vim.HostInternetScsiHbaChapAuthenticationType.chapRequired,
                chapName=iscsiapi_auth.get_inbound_username(),
                chapSecret=iscsiapi_auth.get_inbound_secret(),
                mutualChapAuthenticationType=vim.HostInternetScsiHbaChapAuthenticationType.chapRequired,
                mutualChapName=iscsiapi_auth.get_outbound_username(),
                mutualChapSecret=iscsiapi_auth.get_outbound_secret())
        return None

    def login_all(self, target, auth=None):
        # this function does "discover" too.
        # "target" is just the ip/port as returned by the fake "discover"
        from pyVmomi import vim
        vmauth = self._iscsiapi_auth_to_vmware_auth(auth)
        iscsi_adapter = self._get_iscsi_host_bus_adapter()
        storage_system = self._get_host_storage_system()
        send_target = vim.HostInternetScsiHbaSendTarget(address=target[0], port=target[1],
                                                        authenticationProperties=vmauth)
        msg = "Adding iSCSI SendTarget. target={}:{}. hba adapter device={}"
        logger.info(msg.format(target[0], target[1], iscsi_adapter.device))
        storage_system.AddInternetScsiSendTargets(iScsiHbaDevice=iscsi_adapter.device, targets=[send_target])

    def logout_all(self, target):
        from pyVmomi import vim
        # this function does "undiscover" too.
        # "target" is an actual Target object as returned from get_discovered_targets
        iscsi_adapter = target.iscsi_adapter
        storage_system = self._get_host_storage_system()
        static_targets = [vim.HostInternetScsiHbaStaticTarget(address=endpoint.get_ip_address(),
                                                              port=endpoint.get_port(),
                                                              iScsiName=target.get_iqn())
                          for endpoint in target.get_endpoints()]
        storage_system.RemoveInternetScsiStaticTargets(iScsiHbaDevice=iscsi_adapter.device, targets=static_targets)
        send_target = vim.HostInternetScsiHbaSendTarget(address=target.get_discovery_endpoint().get_ip_address(),
                                                        port=target.get_discovery_endpoint().get_port())
        storage_system.RemoveInternetScsiSendTargets(iScsiHbaDevice=iscsi_adapter.device, targets=[send_target])

    def get_discovered_targets(self):
        from itertools import groupby
        result = []
        for iscsi_adapter in self._get_all_iscsi_host_bus_adapters():
            for parent, targets in groupby(iscsi_adapter.configuredStaticTarget, lambda target: target.parent):
                if ':' not in parent:
                    logger.debug("parent {!r} is not sendtarget for targets: {}".format(parent, targets))
                    continue
                discovery_endpoint_ip, discovery_endpoint_port = parent.split(":")
                discovery_endpoint = base.Endpoint(discovery_endpoint_ip, int(discovery_endpoint_port))
                endpoints = []
                for target in targets:
                    endpoints.append(base.Endpoint(target.address, target.port))
                iqn = target.iScsiName
                target = base.Target(endpoints, discovery_endpoint, iqn)
                # ugly trick to pass iscsi_adapter - just add this attribute to the target
                target.iscsi_adapter = iscsi_adapter
                result.append(target)
        return result

    def get_sessions(self):
        # this returns very incomplete structures, enough to make get_iscsi_hctl_mappings (for get_connectivty) work
        from infi.dtypes.hctl import HCT
        from pyVmomi import vim
        result = []
        scsi_topology_adapters = self._get_properties().get(SCSI_TOPOLOGY_PROPERTY_PATH, [])
        for scsi_adapter in scsi_topology_adapters:
            for scsi_target in scsi_adapter.target:
                if isinstance(scsi_target.transport, vim.HostInternetScsiTargetTransport):
                    h, c, t = scsi_target.key.split("-")[-1].split(":")
                    hct = HCT(h, int(c), int(t))
                    target = base.Target(None, None, scsi_target.transport.iScsiName)
                    result.append(base.Session(target, None, None, self._get_source_iqn(h), None, hct))
        return result


class ConnectionManagerFactory(object):
    models_by_host_value = {}
    models_by_greenlet = {}

    @classmethod
    def clear(cls):
        cls.models_by_greenlet.clear()
        cls.models_by_host_value.clear()

    @classmethod
    def create(cls, client, hostsystem):
        from infi.pyvmomi_wrapper import get_reference_to_managed_object
        key = get_reference_to_managed_object(hostsystem)
        if (client, key) not in cls.models_by_host_value:
            value = ConnectionManager(client, key)
            cls.models_by_host_value[(client, key)] = value
        return cls.models_by_host_value[(client, key)]

    @classmethod
    def get_id(cls):
        from infi.storagemodel.base.gevent_wrapper import get_id
        return get_id()

    @classmethod
    def get(cls):
        return cls.models_by_greenlet.get(cls.get_id())

    @classmethod
    def set(cls, value):
        current = cls.get_id()
        if value is None:
            try:
                del cls.models_by_greenlet[current]
            except KeyError:
                pass
        else:
            cls.models_by_greenlet[current] = value
        return value
