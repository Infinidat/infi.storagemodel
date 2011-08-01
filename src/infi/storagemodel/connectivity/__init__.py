from ..utils import cached_method, cached_property, clear_cache

class FCConnectivity(object):
    def __init__(self, device, local_port, remote_port):
        super(FCConnectivity, self).__init__()
        self._device = device
        self._local_port = local_port
        self._remote_port = remote_port

    @cached_property
    def initiator_wwn(self):
        return self._local_port.port_wwn

    @cached_property
    def target_wwn(self):
        return self._remote_port.port_wwn

class ISCSIConnectivity(object):
    def __init__(self, device):
        super(ISCSIConnectivity, self).__init__()
        self.device = device

class LocalConnectivity(object):
    pass

class ConnectivityFactoryImpl(object):
    @cached_property
    def fc_hctl_mappings(self):
        from infi.hbaapi import get_ports_generator
        result = {}
        for local_port in get_ports_generator().iter_ports():
            for remote_port in local_port.discovered_ports:
                result[remote_port.hct] = (local_port, remote_port,)
        return result

    def get_by_device_with_hctl(self, device):
        hct = (device.hctl.get_host(), device.hctl.get_channel(), device.hctl.get_target())
        fc_mapping = self.fc_hctl_mappings.get(hct, None)
        if fc_mapping is not None:
            local_port, remote_port = fc_mapping
            return FCConnectivity(device, local_port, remote_port)
        # TODO add iSCSI support
        return LocalConnectivity()

ConnectivityFactory = ConnectivityFactoryImpl()
