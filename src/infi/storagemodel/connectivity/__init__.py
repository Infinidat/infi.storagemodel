from infi.pyutils.lazy import cached_method
from infi.dtypes.wwn import WWN
from infi.dtypes.iqn import IQN
from infi.hbaapi import Port
import six


class FCConnectivity(object):
    """Fibre Channel Connectivity Information """
    def __init__(self, device, local_port, remote_port):
        super(FCConnectivity, self).__init__()
        self._device = device
        self._local_port = local_port
        self._remote_port = remote_port

    @cached_method
    def get_initiator_wwn(self):
        """ Returns the wwpn of the initiator """
        if isinstance(self._local_port, WWN):
            return self._local_port
        if isinstance(self._local_port, Port):
            return WWN(self._local_port.port_wwn)
        return WWN(self._local_port)

    @cached_method
    def get_target_wwn(self):
        """ Returns the wwpn of the target """
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
        return "<{}: Initiator {} <--> Target {}>".format(self.__class__.__name__,
            self.get_initiator_wwn(), self.get_target_wwn())


class LocalConnectivity(object):
    pass


class ISCSIConnectivity(object):
    def __init__(self, device, source_iqn, target_iqn):
        super(ISCSIConnectivity, self).__init__()
        self._device = device
        self._source_iqn = source_iqn
        self._target_iqn = target_iqn

    def get_source_iqn(self):
        if isinstance(self._source_iqn, six.string_types):
            return IQN(self._source_iqn)
        return self._source_iqn

    def get_target_iqn(self):
        if isinstance(self._target_iqn, six.string_types):
            return IQN(self._target_iqn)
        return self._target_iqn

    def __eq__(self, obj):
        return isinstance(obj, ISCSIConnectivity) and \
             self.get_source_iqn() == obj.get_source_iqn() and \
             self.get_target_iqn() == obj.get_target_iqn()

    def __ne__(self, obj):
        return not self.__eq__(obj)

    def __repr__(self):
        return "<{}: Source {} <--> Target {}>".format(self.__class__.__name__,
            self.get_source_iqn(), self.get_target_iqn())


class ConnectivityFactoryImpl(object):
    @cached_method
    def get_iscsi_sessions(self):
        from infi.iscsiapi import get_iscsiapi
        iscsiapi = get_iscsiapi()
        return get_iscsiapi().get_sessions()

    def get_fc_hctl_mappings(self):
        from infi.hbaapi import get_ports_generator
        result = {}
        for local_port in get_ports_generator().iter_ports():
            for remote_port in local_port.discovered_ports:
                result[remote_port.hct] = (local_port, remote_port,)
        return result

    def get_iscsi_hctl_mappings(self):
        from infi.iscsiapi.iscsi_exceptions import NotReadyException
        result = {}
        try:
            for session in self.get_iscsi_sessions():
                hct = (session.get_hct().get_host(), session.get_hct().get_channel(), session.get_hct().get_target())
                result[hct] = (session.get_source_iqn(), session.get_target().get_iqn())
        except (ImportError, NotReadyException):
            return result
        return result

    def get_by_device_with_hctl(self, device):
        hct = (device.get_hctl().get_host(),
               device.get_hctl().get_channel(),
               device.get_hctl().get_target())
        fc_mapping = self.get_fc_hctl_mappings().get(hct, None)
        iscsi_mapping = self.get_iscsi_hctl_mappings().get(hct, None)

        if fc_mapping is not None:
            local_port, remote_port = fc_mapping
            return FCConnectivity(device, local_port, remote_port)
        if iscsi_mapping is not None:
            local_iqn, remote_iqn = iscsi_mapping
            return ISCSIConnectivity(device, local_iqn, remote_iqn)
        return LocalConnectivity()


class CachedConnectivityFactoryImpl(ConnectivityFactoryImpl):
    @cached_method
    def get_fc_hctl_mappings(self):
        return super(CachedConnectivityFactoryImpl, self).get_fc_hctl_mappings()


ConnectivityFactory = CachedConnectivityFactoryImpl()
