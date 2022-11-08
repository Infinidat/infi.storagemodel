from calendar import c
import ipaddress
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
from infinisdk.infinibox import InfiniBox

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
        adapters = [adapter for adapter in self._get_NVMe_Topology() if isinstance(adapter, vim.host.NvmeTopology.Interface) and adapter.connectedController]
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
            adapter_controllers_lists = [adapter.connectedController for adapter in self._get_all_NVMe_adapters()]
            controllers = [controller for adapter_list in adapter_controllers_lists for controller in adapter_list if controller.transportType == 'tcp']
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
        nvme_info = self._get_esxcli().get('nvme.info')
        response = nvme_info.Get()
        try:
            host_nqn = response.HostNQN
        except KeyError:
            raise RuntimeError("HostNQN NOT initialized.")
        return host_nqn

    def get_nvme_adapters(self):
        nvme_info = self._get_esxcli().get('nvme.adapter')
        response = nvme_info.List()
        response = [adapter.Adapter for adapter in response if adapter.Driver == "nvmetcp"]
        return response

    def get_host_nqn(self):
        return [NQN(self._get_host_nqn())]    
       
    def get_source_nqn(self):
        controllers =  [controller.name for controller in self._get_NVMe_controllers() if controller.associatedAdapter.replace("key-vim.host.TcpHba-","") == adapter_name]
        return [NQN(NVMe_controller.name) for NVMe_controller in self._get_NVMe_controllers()]
    
    def _get_host_storage_system(self):
        host = self._client.get_managed_object_by_reference(self._moref)
        return host.configManager.storageSystem

    def _get_adapter_connection_details(self, adapter, response):
            connection_details = []
            adapter = self._adapter
            for controller in response:
                try:
                    ipaddress = controller.TransportAddress
                    subnqn = controller.SubsystemNQN    
                except KeyError as e:
                    logger.debug("Controller not properly configured " + e)
                    continue
                else:
                    connection_details.append({'ipaddress': ipaddress, 'adapter': adapter, 'subsystemnqn': subnqn})   
            return connection_details

    def _connect_subsystem(self, connection_details):
  
        from pyVmomi import vim
        nvme_fabrics = self._get_esxcli().get("nvme.fabrics")
        response = nvme_fabrics.Connect(ipaddress=connection_details['ipaddress'], adapter=connection_details['adapter'], subsystemnqn=connection_details['subsystemnqn'])   
        if type(response) == vim.EsxCLI.CLIFault:
            raise RuntimeError(response.errMsg.join(" "))
        else:
            logger.debug("Controller {} connected".format(str(connection_details)))

    def discover_adapter(self, discover_endpoint, adapter):
        
        nvme_fabrics = self._get_esxcli().get('nvme.fabrics')
        response = nvme_fabrics.Discover(ipaddress=discover_endpoint, adapter=adapter)
        if response:
            return self._get_adapter_connection_details(adapter, response)
        else:
            raise ValueError("Details from {} can not be parserd".format(adapter))
    
    def discover(self, discover_endpoint):
        nvme_targets = []
        topology = self._get_NVMe_Topology()
        for adapter in self.get_nvme_adapters():
            nvme_targets.extend(self.discover_adapter(discover_endpoint, adapter))
        return nvme_targets

    def connect_adapters(self, nvme_targets):
        if nvme_targets:
            for target in nvme_targets:
                try:
                    self._connect_subsystem(target)
                except RuntimeError:
                        raise RuntimeError("Controller already {} conneted. NVMe connection for {} can not be established".format(str(connection_details), name))
        else:
            raise RuntimeError("No configred NVMe controllers. NVMe connection for {} can not be established.".format(name))


    def _disconnect_subsystem(self, connection_details):
        nvme_fabrics = self._get_esxcli().get('nvme.fabrics')
        import pdb; pdb.set_trace()
        response = nvme_fabrics.Disconnect(adapter=connection_details["adapter"], subsystemnqn=connection_details["subsystemnqn"])
        if type(response) == str:
            raise RuntimeError(response)
        else:
            logger.debug("Controller {} disconnected".format(str(connection_details)))   

    def _get_controllers_connection_details(self, controller):
        serial = str.strip(controller.serialNumber)
        connection_data = controller.name.split("#")
        connection_details = {'ipaddress': connection_data[-1], 'adapter': connection_data[-2], 'subsystemnqn': controller.subnqn}
        return serial, connection_details


    def disconnect_all_adapters_by_serial(self, system_serial):
        for controller in self._get_NVMe_controllers():
            serial, connection_details = self._get_controllers_connection_details(controller)
            if serial == str(system_serial):
                try:
                    self._disconnect_subsystem(connection_details)
                except RuntimeError:
                    raise RuntimeError("Controller already {} NOT conneted. NVMe connection for {} can not be disconnected".format(str(connection_details), name))


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

