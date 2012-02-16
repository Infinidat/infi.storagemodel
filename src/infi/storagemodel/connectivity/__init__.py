
from infi.pyutils.lazy import cached_method, clear_cache, LazyImmutableDict
from infi.dtypes.wwn import WWN
from infi.hbaapi import Port

class FCConnectivity(object):
    """Fibre Channel Connectivity Information """
    def __init__(self, device, local_port, remote_port):
        super(FCConnectivity, self).__init__()
        self._device = device
        self._local_port = local_port
        self._remote_port = remote_port

    @cached_method
    def get_initiator_wwn(self):
        """:returns: the wwpn of the initiator"""
        if isinstance(self._local_port, WWN):
            return self._local_port
        if isinstance(self._local_port, Port):
            return WWN(self._local_port.port_wwn)
        return WWN(self._local_port)

    @cached_method
    def get_target_wwn(self):
        """:returns: the wwpn of the target"""
        if isinstance(self._remote_port, WWN):
            return self._remote_port
        if isinstance(self._remote_port, Port):
            return WWN(self._remote_port.port_wwn)
        return WWN(self._remote_port)

    def __eq__(self, obj):
        return isinstance(obj, FCConnectivity) and \
             self.get_initiator_wwn() == obj.get_initiator_wwn() and \
             self.get_target_wwn() == obj.get_target_wwn()

    def __ne__(self, obj):
        return not self.__eq__(obj)

    def __repr__(self):
        return "<FCConnectivity: Initiator {} <--> Target {}>".format(self.get_initiator_wwn(), self.get_target_wwn())

class LocalConnectivity(object):
    pass

class ConnectivityFactoryImpl(object):
    @cached_method
    def get_fc_hctl_mappings(self):
        from infi.hbaapi import get_ports_generator
        result = {}
        for local_port in get_ports_generator().iter_ports():
            for remote_port in local_port.discovered_ports:
                result[remote_port.hct] = (local_port, remote_port,)
        return result

    def get_by_device_with_hctl(self, device):
        hct = (device.get_hctl().get_host(),
               device.get_hctl().get_channel(),
               device.get_hctl().get_target())
        fc_mapping = self.get_fc_hctl_mappings().get(hct, None)
        if fc_mapping is not None:
            local_port, remote_port = fc_mapping
            return FCConnectivity(device, local_port, remote_port)
        # TODO add iSCSI support
        return LocalConnectivity()

ConnectivityFactory = ConnectivityFactoryImpl()
