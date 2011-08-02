
from ..utils import cached_method, clear_cache

class PredicateList(object):
    """returns True if all predicates in a given list return True"""
    def __init__(self, list_of_predicates):
        super(PredicateList, self).__init__()
        self._list_of_predicates = list_of_predicates

    def __call__(self):
        return all([predicate() for predicate in self._list_of_predicates])

class DiskExists(object):
    """returns True if a disk was discovered with scsi_serial_number"""

    def __init__(self, scsi_serial_number):
        super(DiskExists, self).__init__()
        self.scsi_serial_number = scsi_serial_number

    def __call__(self):
        from .. import get_storage_model
        model = get_storage_model()
        # TODO check vmalloc/functors
        block_devices = model.get_scsi().get_all_scsi_block_devices()
        mp_devices = model.get_native_multipath().get_all_multipath_devices()
        # TODO create get all non-multipath-devices 
        non_mp_devices = model.get_native_multipath().filter_non_multipath_scsi_block_devices(block_devices)
        return any([device.scsi_serial_number == device.scsi_serial_number for device in mp_devices + non_mp_devices])

class DiskNotExists(DiskExists):
    """returns True if a disk with scsi_serial_number has gone away"""

    def __call__(self):
        return not super(DiskNotExists, self).__call__()

class LunExists(object):
    """returns True if a lun mapping was discovered"""

    #TODO different predicates for fiber, iscsi
    def __init__(self, connectivity, lun_number):
        """ see classmethods by_iscsi, by_fc)"""
        super(LunExists, self).__init__()
        self.connectivity = connectivity
        self.lun_number = lun_number

    @classmethod
    def by_iscsi(cls):
        # TODO later
        raise NotImplementedError

    @classmethod
    def by_fc(cls, initiator_wwn, target_wwn, lun_number):
        from infi.hbaapi import Port

        from ..connectivity import FCConnectivity
        i_port = Port()
        i_port.port_wwn = initiator_wwn
        t_port = Port()
        t_port.port_wwn = target_wwn
        return cls(FCConnectivity(None, i_port, t_port), lun_number)

    def _is_fc_connectivity_a_match(self, device):
        from ..connectivity import FCConnectivity, ISCSIConnectivity
        if isinstance(device.connectivity, FCConnectivity) and isinstance(self.connectivity, FCConnectivity):
            if device.connectivity.get_initiator_wwn == self.connectivity.get_initiator_wwn:
                if device.connectivity.get_target_wwn == self.connectivity.get_target_wwn:
                    if device.get_hctl.get_lun() == self.lun_number:
                        return True
        return False

    def __call__(self):
        from .. import get_storage_model
        model = get_storage_model()
        for device in model.get_scsi().get_all_scsi_block_devices():
            if self._is_fc_connectivity_a_match(device):
                return True
            # TODO add iSCSI support
        for device in model.get_native_multipath().get_all_multipath_devices():
            for path in device.get_paths:
                if self._is_fc_connectivity_a_match(path):
                    return True
                # TODO add iSCSI support
        return False

class LunNotExists(LunExists):
    """returns True if a lun un-mapping was discovered"""
    def __call__(self):
        return not super(LunNotExists, self).__call__()
