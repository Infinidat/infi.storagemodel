from .infi import nvmeapi
from .infi.nvmeapi import base
#from .infi.nvmeapi import auth as nvmeapi_auth_module
from infi.pyutils.contexts import contextmanager
from infi.pyutils.patch import monkey_patch
from infi.dtypes.nqn import NQN
from logging import getLogger


logger = getLogger(__name__)


PROPERTY_COLLECTOR_KEY = 'infi.nvmeapi'
HBAAPI_PROPERTY_PATH = 'config.storageDevice.hostBusAdapter'
NVME_TOPOLOGY_PROPERTY_PATH = 'config.storageDevice.NvmeTopology.adapter'


def install_property_collectors_on_client(client):
    from infi.pyvmomi_wrapper.property_collector import HostSystemCachedPropertyCollector
    if PROPERTY_COLLECTOR_KEY in client.property_collectors:
        return
    collector = HostSystemCachedPropertyCollector(client, [HBAAPI_PROPERTY_PATH])
    client.property_collectors[PROPERTY_COLLECTOR_KEY] = collector


@contextmanager
def with_host(client, host):
    from infi.pyvmomi_wrapper import get_reference_to_managed_object
    monkey_patch(infi.nvmeapi, "get_nvmeapi", ConnectionManagerFactory.get)
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

    def _get_all_NVMe_host_bus_adapters(self):
        from pyVmomi import vim
        all_host_bus_adapters = self._get_all_host_bus_adapters()
        logger.debug("all_host_bus_adapters = {}".format([(adapter.device, type(adapter)) for adapter in all_host_bus_adapters]))
        return [adapter for adapter in all_host_bus_adapters if isinstance(adapter, vim.host.HostBusAdapter) and adapter.driver == "nvmetcp"]

    def _get_NVMe_host_bus_adapter(self, adapter=None):
        # the host bus adapter to retrieve can be either from parameter (specific adapter requested by caller, e.g. to
        # get NQN of specific session where adapter is known) or from 'set_adapter' (default adapter that caller wants
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
            adapters = [adapter for adapter in adapters if adapter.driver == 'nvmetcp']
        if len(adapters) == 0:
            raise RuntimeError("No matching NVMe adatpers found on host.")
        return adapters[0]

    def _get_host_storage_system(self):
        host = self._client.get_managed_object_by_reference(self._moref)
        return host.configManager.storageSystem

    def _get_source_nqn(self, adapter=None):
        # this get_source_nqn returns a single NQN for the currently used hba
        # the external get_source_nqn returns all NQNs (from all adapters), in order for 'register' to register all
        # available NQNs on host
        NVMe_adapter = self._get_NVMe_host_bus_adapter(adapter)
        return NQN(NVMe_adapter.NVMeName)

    def get_source_nqn(self):
        import pdb; pdb.set_trace()
        adaptrs = self._get_all_NVMe_host_bus_adapters()
        return [NQN(NVMe_adapter.NVMeName) for NVMe_adapter in self._get_all_NVMe_host_bus_adapters()]

    def set_source_NQN(self, NQN):
        _ = NQN(NQN)   # checks NQN is valid
        self._get_host_storage_system().UpdateInternetScsiName(self._get_source_nqn(), NQN)

    def discover(self, ip_address, port=3260):
        # ugly trick: in VMware discovery and login_all happen at once, so we don't do the login here
        # and don't return a real "Target" object. Everything happens in login_all
        return (ip_address, port)

    def undiscover(self, target=None):
        # real undiscover happens with "logout_all"
        pass

    def login_all(self, target, auth=None):
        # this function does "discover" too.
        # "target" is just the ip/port as returned by the fake "discover"
        from pyVmomi import vim
        vmauth = None
        NVMe_adapter = self._get_NVMe_host_bus_adapter()
        storage_system = self._get_host_storage_system()
        send_target = vim.HostInternetScsiHbaSendTarget(address=target[0], port=target[1],
                                                        authenticationProperties=vmauth)
        msg = "Adding NVMe SendTarget. target={}:{}. hba adapter device={}"
        logger.info(msg.format(target[0], target[1], NVMe_adapter.device))
        storage_system.AddInternetScsiSendTargets(NVMeHbaDevice=NVMe_adapter.device, targets=[send_target])

    def logout_all(self, target):
        from pyVmomi import vim
        # this function does "undiscover" too.
        # "target" is an actual Target object as returned from get_discovered_targets
        NVMe_adapter = target.NVMe_adapter
        storage_system = self._get_host_storage_system()
        static_targets = [vim.HostInternetScsiHbaStaticTarget(address=endpoint.get_ip_address(),
                                                              port=endpoint.get_port(),
                                                              NVMeName=target.get_NQN())
                          for endpoint in target.get_endpoints()]
        storage_system.RemoveInternetScsiStaticTargets(NVMeHbaDevice=NVMe_adapter.device, targets=static_targets)
        send_target = vim.HostInternetScsiHbaSendTarget(address=target.get_discovery_endpoint().get_ip_address(),
                                                        port=target.get_discovery_endpoint().get_port())
        storage_system.RemoveInternetScsiSendTargets(NVMeHbaDevice=NVMe_adapter.device, targets=[send_target])

    def get_discovered_targets(self):
        from itertools import groupby
        result = []
        for NVMe_adapter in self._get_all_NVMe_host_bus_adapters():
            for parent, targets in groupby(NVMe_adapter.configuredStaticTarget, lambda target: target.parent):
                if ':' not in parent:
                    logger.debug("parent {!r} is not sendtarget for targets: {}".format(parent, targets))
                    continue
                discovery_endpoint_ip, discovery_endpoint_port = parent.split(":")
                discovery_endpoint = base.Endpoint(discovery_endpoint_ip, int(discovery_endpoint_port))
                endpoints = []
                for target in targets:
                    endpoints.append(base.Endpoint(target.address, target.port))
                NQN = target.NVMeName
                target = base.Target(endpoints, discovery_endpoint, NQN)
                # ugly trick to pass NVMe_adapter - just add this attribute to the target
                target.NVMe_adapter = NVMe_adapter
                result.append(target)
        return result

    def get_sessions(self):
        # this returns very incomplete structures, enough to make get_NVMe_hctl_mappings (for get_connectivty) work
        from infi.dtypes.hctl import HCT
        from pyVmomi import vim
        import pdb; pdb.set_trace()
        result = []
        nvme_topology_adapters = self._get_properties(NVME_TOPOLOGY_PROPERTY_PATH, [])
        for nvme_adapter in nvme_topology_adapters:
            for nvme_target in nvme_adapter.target:
                if isinstance(nvme_target.transport, vim.HostInternetScsiTargetTransport):
                    h, c, t = nvme_target.key.split("-")[-1].split(":")
                    hct = HCT(h, int(c), int(t))
                    source_NQN = self._get_source_nqn(h)
                    target_NQN = nvme_target.transport.NVMeName
                    msg = "get_sessions: adding session for target with NQN {} from NQN {}. HCT {}"
                    logger.debug(msg.format(target_NQN, source_NQN, hct))
                    target = base.Target(None, None, target_NQN)
                    result.append(base.Session(target, None, None, source_NQN, None, hct))
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
