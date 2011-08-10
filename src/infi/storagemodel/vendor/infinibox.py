
from infi.pyutils.lazy import cached_method
from . import VendorMultipathDevice, VendorSCSIBlockDevice, VendorSCSIStorageController

class InfiniBoxMixin(object):
    @cached_method
    def get_box_ipv4_address(self):
        return ''

class block_class(InfiniBoxMixin, VendorSCSIBlockDevice):
    pass

class controller_class(InfiniBoxMixin, VendorSCSIStorageController):
    pass

class multipath_class(InfiniBoxMixin, VendorMultipathDevice):
    pass

vid_pid = ("NFINIDAT" , "Infinidat A01")

class InfinidatVolumeExists(object):
    """A predicate that checks if an Infinidat volume exists"""
    def __init__(self, infinipy_volume):
        self.infinipy_volume = infinipy_volume

    def __call__(self):
        from .. import get_storage_model
        model = get_storage_model()
        scsi = model.get_scsi()
        mpath = model.get_native_multipath()
        block_devices = scsi.filter_vendor_specific_devices(scsi.get_all_scsi_block_devices(), vid_pid)
        mp_devices = mpath.filter_vendor_specific_devices(mpath.get_all_multipath_devices(), vid_pid)
        non_mp_devices = mpath.filter_non_multipath_scsi_block_devices(block_devices)
        return any([device.volume_name == self.infinipy_volume.get_name() for device in mp_devices + non_mp_devices])
