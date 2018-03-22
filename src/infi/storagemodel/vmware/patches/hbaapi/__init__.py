from infi.dtypes.wwn import WWN
from infi.hbaapi import Port
from infi.hbaapi.generators import Generator
from infi.pyutils.contexts import contextmanager
from logging import getLogger

logger = getLogger(__name__)

PROPERTY_COLLECTOR_KEY = 'infi.hbaapi'
HBAAPI_PROPERTY_PATH = 'config.storageDevice.hostBusAdapter'
SCSI_TOPOLOGY_PROPERTY_PATH = 'config.storageDevice.scsiTopology.adapter'

def install_property_collectors_on_client(client):
    from infi.pyvmomi_wrapper.property_collector import HostSystemCachedPropertyCollector
    if PROPERTY_COLLECTOR_KEY in client.property_collectors:
        return
    collector = HostSystemCachedPropertyCollector(client,
                                                  [HBAAPI_PROPERTY_PATH, SCSI_TOPOLOGY_PROPERTY_PATH])
    client.property_collectors[PROPERTY_COLLECTOR_KEY] = collector

class HostSystemPortGenerator(Generator):
    def __init__(self, client, moref):
        super(HostSystemPortGenerator, self).__init__()
        self._moref = moref
        self._client = client

    @classmethod
    def is_available(cls):
        return True

    def _install_property_collector(self):
        install_property_collectors_on_client(self._client)

    def _get_properties(self):
        properties = self._client.property_collectors[PROPERTY_COLLECTOR_KEY].get_properties().get(self._moref, dict())
        return properties

    def _get_all_host_bus_adapters(self):
        return self._get_properties().get(HBAAPI_PROPERTY_PATH, [])

    def _get_all_fiber_channel_host_bus_adapters(self):
        from pyVmomi import vim
        FCHBA_CLASS = vim.host.FibreChannelHba
        return [adapter for adapter in self._get_all_host_bus_adapters() if isinstance(adapter, FCHBA_CLASS)]

    def _translate_long_to_wwn(self, wwn_long):
        return WWN(hex(wwn_long)[:-1])

    def _get_all_scsi_topologies(self):
        return self._get_properties().get(SCSI_TOPOLOGY_PROPERTY_PATH, [])

    def _get_target_transport_properties(self, fc_hba, target):
        return target.transport

    def _populate_remote_port(self, fc_hba, target):
        properties = self._get_target_transport_properties(fc_hba, target)
        # http://vijava.sourceforge.net/vSphereAPIDoc/ver5/ReferenceGuide/vim.host.ScsiTopology.Target.html
        port = Port()
        port.port_wwn = self._translate_long_to_wwn(properties.portWorldWideName)
        logger.debug("Found remote port with address {}".format(port.port_wwn))
        port.node_wwn = self._translate_long_to_wwn(properties.nodeWorldWideName)
        port.hct = (fc_hba.device, 0, target.target)
        return port

    def _populate_remote_ports(self, fc_hba):
        all_adapter_topologies = self._get_all_scsi_topologies()
        adapter_topology = [topology for topology in all_adapter_topologies if topology.adapter == fc_hba.key]
        remote_ports = []
        for target in adapter_topology[0].target:
            if target.transport.portWorldWideName:  # If target in "dead or error" state, then portWorldWideName is 0
                remote_ports.append(self._populate_remote_port(fc_hba, target))
        return remote_ports

    def _populate_port(self, fc_hba):
        # http://vijava.sourceforge.net/vSphereAPIDoc/ver5/ReferenceGuide/vim.host.HostBusAdapter.html
        port = Port()
        port.port_wwn = self._translate_long_to_wwn(fc_hba.portWorldWideName)
        logger.debug("Found local port with address {}".format(port.port_wwn))
        port.node_wwn = self._translate_long_to_wwn(fc_hba.nodeWorldWideName)
        port.port_speed = int(fc_hba.speed)
        port.port_supported_speeds = [port.port_speed, ]
        port.port_type = fc_hba.portType
        port.port_state = fc_hba.status
        port.model_description = fc_hba.model
        port.driver_name = fc_hba.driver
        port.os_device_name = fc_hba.device
        port.discovered_ports = self._populate_remote_ports(fc_hba)
        port.hct = (fc_hba.device, -1, -1)
        return port

    def iter_ports(self):
        self._install_property_collector()
        for fc_hba in self._get_all_fiber_channel_host_bus_adapters():
            yield self._populate_port(fc_hba)


class HostSystemPortGeneratorFactory(object):
    patches_by_greenlet = {}

    @classmethod
    def clear(cls):
        cls.patches_by_greenlet.clear()

    @classmethod
    def create(cls, client, hostsystem):
        from infi.pyvmomi_wrapper import get_reference_to_managed_object
        key = get_reference_to_managed_object(hostsystem)
        class Patched(HostSystemPortGenerator):
            def __init__(self):
                super(Patched, self).__init__(client, key)
        return [Patched]

    @classmethod
    def get_id(cls):
        from infi.storagemodel.base.gevent_wrapper import get_id
        return get_id()

    @classmethod
    def get(cls):
        return cls.patches_by_greenlet.get(cls.get_id())

    @classmethod
    def set(cls, value):
        cls.patches_by_greenlet[cls.get_id()] = value


import infi.hbaapi.generators
from infi.pyutils.patch import monkey_patch

@contextmanager
def with_host(client, host):
    monkey_patch(infi.hbaapi.generators, "get_list_of_generators", HostSystemPortGeneratorFactory.get)
    previous = HostSystemPortGeneratorFactory.get()
    try:
        HostSystemPortGeneratorFactory.set(HostSystemPortGeneratorFactory.create(client, host))
        yield
    finally:
        HostSystemPortGeneratorFactory.set(previous)
