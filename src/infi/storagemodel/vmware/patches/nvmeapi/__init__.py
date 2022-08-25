from calendar import c
from pprint import pp
import re
from sqlite3 import adapters

from .infi import nvmeapi
from .infi.nvmeapi import base
#from .infi.nvmeapi import auth as nvmeapi_auth_module
from infi.pyutils.contexts import contextmanager
from infi.pyutils.patch import monkey_patch
from infi.dtypes.nqn import NQN
from logging import getLogger
from infi.pyvmomi_wrapper.esxcli import EsxCLI   

logger = getLogger(__name__)


PROPERTY_COLLECTOR_KEY = 'infi.nvmeapi'
#HBAAPI_PROPERTY_PATH = 'config.storageDevice.hostBusAdapter'
HBAAPI_PROPERTY_PATH = 'config.storageDevice.hostBusAdapter'
NVME_TOPOLOGY_PROPERTY_PATH = 'config.storageDevice.nvmeTopology.adapter'
#NVME_TOPOLOGY_PROPERTY_PATH = 'config.storageDevice'

def install_property_collectors_on_client(client):
    from infi.pyvmomi_wrapper.property_collector import HostSystemCachedPropertyCollector
    if PROPERTY_COLLECTOR_KEY in client.property_collectors:
        return
    collector = HostSystemCachedPropertyCollector(client, [HBAAPI_PROPERTY_PATH, NVME_TOPOLOGY_PROPERTY_PATH])
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


    def _get_NVMe_Topology(self):
        return self._get_properties().get(NVME_TOPOLOGY_PROPERTY_PATH, [])


    def get_all_NVMe_host_bus_adapters(self):
        from pyVmomi import vim
        all_host_bus_adapters = self._get_all_host_bus_adapters()
        logger.debug("all_host_bus_adapters = {}".format([(adapter.device, type(adapter)) for adapter in all_host_bus_adapters]))
        return [adapter for adapter in all_host_bus_adapters if isinstance(adapter, vim.host.HostBusAdapter) and adapter.driver == "nvmetcp"]


    def _get_all_NVMe_adapters(self):
        from pyVmomi import vim
        import pdb; pdb.set_trace()
        adapters = [adapter for adapter in self._get_NVMe_Topology() if isinstance(adapter, vim.host.NvmeTopology.Interface) and adapter.driver == "nvmetcp"]
        return adapters
    
    def get_all_NVMe_adapters_ids(self):
        return [adapter.adapter.replace("key-vim.host.TcpHba-","") for adapter in self._get_all_NVMe_adapters()]
  
    def _get_NVMe_controllers(self, specifiedadapter=None):
        from pyVmomi import vim
        # the host bus adapter to retrieve can be either from parameter (specific adapter requested by caller, e.g. to
        # get NQN of specific session where adapter is known) or from 'set_adapter' (default adapter that caller wants
        # to work with - e.g. to login) or None for default behavior (use the software adapter)
        # adapter
        if specifiedadapter:
            return [adapter.connectedController for adapter in self._get_all_NVMe_adapters() if isinstance(adapter.connectedController, vim.host.NvmeController) and adapter == specifiedadapter]
        else:
            import pdb; pdb.set_trace()
            controllers = [controller for adapter.connectedController in self._get_all_NVMe_adapters() for controller in controller.connectedController if isinstance(controller, vim.host.NvmeController)]
            return controllers

    def _get_host_storage_system(self):
        host = self._client.get_managed_object_by_reference(self._moref)
        return host.configManager.storageSystem

    def _get_esxcli(self):
        from infi.vendata.vmware_powertools.vcenter.shortcuts import moref_to_object
        host  = moref_to_object(self._moref)
        esxcli = EsxCLI(host)
        esxcli._load_datatypes()
        return esxcli

    def _get_host_nqn(self):
        import pdb; pdb.set_trace()
        nvme_info = self._get_esxcli().get('nvme.info')
        response = nvme_info.Get()
        try:
            host_nqn = response.HostNQN
        except KeyError:
            raise RuntimeError("HostNQN NOT initialized.")
        return host_nqn

    def get_nvme_adapters(self):
        import pdb; pdb.set_trace()
        from pyVmomi import vim
        nvme_info = self._get_esxcli().get('nvme.adapter')
        response = nvme_info.List()
        response = [adapter.Adapter for adapter in response if adapter.Driver == "nvmetcp"]
        return response

    def get_host_nqn(self):
        return [NQN(self._get_host_nqn())]    
       
    def get_source_nqn(self):
        import pdb; pdb.set_trace()
        controllers =  [controller.name for controller in self._get_NVMe_controllers() if controller.associatedAdapter.replace("key-vim.host.TcpHba-","") == adapter_name]
        return [NQN(NVMe_controller.name) for NVMe_controller in self._get_NVMe_controllers()]

    def get_connection_details(self, controller):
        name = controller.name
        details = name.split('#')
        if len(details) == 3: 
            ip = details[2].split(':')[0]
            adapter = details[1]
            subnqn = details[2]
            connection_details = {'ipaddress': ip, 'adapter': adapter, 'subsystemnqn': subnqn}
            return connection_details
        else:
            raise ValueError("Details from {} can not be parserd".format(name))

    def _connect_subsystem(self, connection_details):
        nvme_fabrics = self._get_esxcli().get("nvme.fabrics")
        response = nvme_fabrics.Connect(connection_details)
        if type(response) == str:
            raise RuntimeError(response)
        else:
            logger.debug("Controller {} connected".format(str(connection_details)))
     
    def discover_adapter(self, discover_endpoint, adapter):
        import pdb; pdb.set_trace()
        nvme_fabrics = self._get_esxcli().get('nvme.fabrics')
        response = nvme_fabrics.Discover(ip=discover_endpoint, a=adapter)
        return response
    
    def discover(self, discover_endpoint):
        nvme_targets = []
        for adapter in self.get_nvme_adapters():
            nvme_targets.append(self.discover_adapter(discover_endpoint, adapter))
        return nvme_targets

    def connect_adapters(self, nvme_targets):
        for target in nvme_targets:
            connection_details = self.get_connection_details(target)
            try:
                self._connect_subsystem(connection_details)
            except RuntimeError:
                    raise RuntimeError("Controller already {} conneted. NVMe connection for {} can not be established".format(str(connection_details), name))
        else:
            raise RuntimeError("No configred NVMe controllers. NVMe connection for {} can not be established.".format(name))

    def _disconnect_subsystem(self, connection_details):
        nvme_fabrics = self._get_esxcli().get('nvme.fabrics')
        response = nvme_fabrics.Disconnect(connection_details)
        if type(response) == str:
            raise RuntimeError(response)
        else:
            logger.debug("Controller {} connected".format(str(connection_details)))   

    def disconnect_all_adapters(self, adapter=None):
        controllers = self._get_NVMe_controllers()
        if controllers:
            for controller in controllers:
                connection_details = self.get_connection_details(controller)
                try:
                    self._disconnect_subsystem(connection_details)
                except RuntimeError:
                        raise RuntimeError("Controller already {} conneted. NVMe connection for {} can not be established".format(str(connection_details), name))
        else:
            raise RuntimeError("No configred NVMe controllers. NVMe connection for {} can not be established.".format(name))

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
