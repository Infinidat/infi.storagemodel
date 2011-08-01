
from ..utils import cached_property, clear_cache

class LunInventoryChanged(object):
    def __init__(self):
        self.baseline = self._get_snapshot()

    def _get_snapshot(self):
        from .. import get_storage_model
        model = get_storage_model()
        disks = model.scsi.get_all_scsi_block_devices()
        hctl_mappings = {}
        for disk in disks:
            hctl_mappings[disk.hctl] = disk.scsi_serial_number
        return hctl_mappings

    def __call__(self):
        current = self._get_snapshot()
        # find new disks
        for disk in current:
            if disk.hctl not in self.baseline.keys():
                return True
        # find removed disks
        for disk in self.baseline:
            if disk.hctl not in current.keys():
                return True
        return False


class PredicateList(object):
    def __init__(self, list_of_predicates):
        super(PredicateList, self).__init__()
        self._list_of_predicates = list_of_predicates

    def __call__(self):
        for predicate in self._list_of_predicates:
            if predicate():
                return True
        return False

class DiskArrived(object):
    """returns True if a disk was discovered with scsi_serial_number"""

    def __init__(self, scsi_serial_number):
        super(DiskArrived, self).__init__()
        self.scsi_serial_number = scsi_serial_number

    def __call__(self):
        from .. import get_storage_model
        model = get_storage_model()
        for device in model.native_multipath.get_all_multipath_devices():
            if device.scsi_serial_number == self.scsi_serial_number:
                return True
        for device in model.scsi.get_all_scsi_block_devices():
            if device.scsi_serial_number == self.scsi_serial_number:
                return True
        return False

class DiskWentAway(DiskArrived):
    """returns True if a disk with scsi_serial_number has gone away"""

    def __call__(self):
        return not super(DiskWentAway, self).__init__()

class NewLunMapping(object):
    """returns True if a lun mapping was discovered"""

    def __init__(self, connectivity, lun_number):
        """ see classmethods by_iscsi, by_fc)"""
        super(NewLunMapping, self).__init__()
        self.connectivity = connectivity
        self.lun_number

    @classmethod
    def by_iscsi(cls):
        # TODO later
        raise NotImplementedError

    @classmethod
    def by_fc(cls, initiator_wwn, target_wwn, lun_number):
        from infi.hbaapi import Port

        from ..connectivity import FCConnectivity
        return cls(FCConnectivity(None, Port(port_wwn=initiator_wwn), Port(port_wwn=target_wwn),
                                  lun_number))

    def _is_fc_connectivity_a_match(self, device):
        from ..connectivity import FCConnectivity, ISCSIConnectivity
        if isinstance(device, FCConnectivity) and isinstance(self.connectivty, FCConnectivity):
            if device.connectivity.initiator_wwn == self.connectivity.initiator_wwn:
                if device.connectivity.target__wwn == self.connectivity.target_wwn:
                    if device.hctl.get_lun() == self.lun_number:
                        return True
        return False

    def __call__(self):
        from .. import get_storage_model
        model = get_storage_model()
        for device in model.scsi.get_all_scsi_block_devices():
            if self._is_fc_connectivity_a_match(device):
                return True
            # TODO add iSCSI support
        for device in model.native_multipath.get_all_multipath_devices():
            for path in device.paths:
                if self._is_fc_connectivity_a_match(path):
                    return True
                # TODO add iSCSI support
        return False

class LunWentAway(NewLunMapping):
    """returns True if a lun un-mapping was discovered"""
    def __call__(self):
        return not super(LunWentAway, self)()

class SnapshotHasChanged(object):
    """This predicate is for applications who are interested in devices that were added/removed.
    It takes a "snapshot" of the current model during initialization, which is considered a "baseline".
    When called, the current "snapshot" is compared to the "baseline" and returns True if: 
    * there is a "difference" between the "snapshot" and the "baseline", where a difference is:
    ** a device (either a MultipathDevice or SCSIBlockDevice) was added or removed.
    
    Notes:
    * No other changes (e.g. path add/removal) was considered.
    * Devices are matches by their scsi_serial_number, behavior for devices with scsi_serial_number="" is undefined.
    * The removed_devices property returns a list of devices will all their properties pre-populated.
    ** This means that you can query the scsi_standard_inquiry of a removed device, since it was pre-cached.
    ** Because of this, this predicate is not cheap."""

    def __init__(self):
        super(SnapshotHasChanged, self).__init__()
        self.baseline = self.create_snapshot(True)
        self.current = {}
        self._removed_devices = []
        self._added_devices = []

    def create_snapshot(self, populate_cache=False):
        from inspect import getmembers
        from .. import get_storage_model
        model = get_storage_model()
        scsi_block_devices = model.scsi.get_all_scsi_block_devices()
        mp_devices = model.native_multipath.get_all_multipath_devices()
        non_mp_devices = model.native_multipath.filter_non_multipath_scsi_block_devices(scsi_block_devices)
        devices = {}
        for device in mp_devices:
            _ = getmembers(device) if populate_cache else None
            devices[device.scsi_serial_number] = device
        for device in non_mp_devices:
            _ = getmembers(device) if populate_cache else None
            devices[device.scsi_serial_number] = device
        return devices

    def __call__(self):
        self.current = self.create_snapshot()
        if self.added_devices == [] and self.removed_devices == []:
            clear_cache(self)
            return False

    @cached_property
    def added_devices(self):
        """returns a list of devices that were added in the rescan"""
        return filter(lambda device: device.scsi_serial_number not in self.baseline,
                      self.current.values())

    @cached_property
    def removed_devices(self):
        """returns a list of devices that were removed in the rescan"""
        return filter(lambda device: device.scsi_serial_number not in self.current_values,
                      self.baseline.values())
