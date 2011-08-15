
from infi.pyutils.lazy import cached_method
from . import VendorMultipathDevice, VendorSCSIBlockDevice, VendorSCSIStorageController

class InfiniBoxMixin(object):
    @cached_method
    def get_box_ipv4_address(self):
        """:returns: the management IPv4 address of the InfiniBox
        :rtype: string"""
        from infi.asi.cdb.inquiry.vpd_pages.device_identification.designators import SCSINameDesignator
        device_identification_page = self.device.get_scsi_inquiry_pages()[0x83]
        for designator in device_identification_page.designators_list:
            if isinstance(designator, SCSINameDesignator) and designator.scsi_name_string.startswith("ip"):
                return designator.scsi_name_string.split("=")[1].strip()

    @cached_method
    def get_host_name(self):
        """:returns: the host name within the InfiniBox
        :rtype: string"""
        from infi.asi.cdb.inquiry.vpd_pages.device_identification.designators import SCSINameDesignator
        device_identification_page = self.device.get_scsi_inquiry_pages()[0x83]
        for designator in device_identification_page.designators_list:
            if isinstance(designator, SCSINameDesignator) and designator.scsi_name_string.startswith("host"):
                return designator.scsi_name_string.split("=")[1].strip()

class InfiniBoxVolumeMixin(object):
    @cached_method
    def _is_volume_mapped(self):
        """In race condition between a rescan and volume unmap operation, the device may stil exists while there volume
        is already unampped.
        :returns: this method returns True if a volume is mapped to the device."""
        standard_inquiry = self.device.get_scsi_standard_inquiry()
        # spc4r30 section 6.4.2 tables 140 + 141, peripheral device type 0 is disk, 31 is unknown or no device
        return standard_inquiry.peripheral_device.type == 0

    @cached_method
    def get_volume_name(self):
        """:returns: the volume name within the InfiniBox
        :rtype: string"""
        from infi.asi.cdb.inquiry.vpd_pages.device_identification.designators import SCSINameDesignator
        # TODO remove the following clause after INFINIBOX-31 is resolved:
        if not self._is_volume_mapped():
            return "(none)"
        device_identification_page = self.device.get_scsi_inquiry_pages()[0x83]
        for designator in device_identification_page.designators_list:
            if isinstance(designator, SCSINameDesignator) and designator.scsi_name_string.startswith("vol"):
                return designator.scsi_name_string.split("=")[1].strip()

class block_class(InfiniBoxMixin, InfiniBoxVolumeMixin, VendorSCSIBlockDevice):
    pass

class controller_class(InfiniBoxMixin, VendorSCSIStorageController):
    pass

class multipath_class(InfiniBoxMixin, InfiniBoxVolumeMixin, VendorMultipathDevice):
    pass

vid_pid = ("NFINIDAT" , "Infinidat A01")

class InfinidatVolumeExists(object):
    """A predicate that checks if an Infinidat volume exists"""
    def __init__(self, volume_name):
        self.volume_name = volume_name

    def __call__(self):
        from .. import get_storage_model
        model = get_storage_model()
        scsi = model.get_scsi()
        mpath = model.get_native_multipath()
        block_devices = scsi.filter_vendor_specific_devices(scsi.get_all_scsi_block_devices(), vid_pid)
        # TODO remove these comments after the linux implementation is complete
        #mp_devices = mpath.filter_vendor_specific_devices(mpath.get_all_multipath_devices(), vid_pid)
        #non_mp_devices = mpath.filter_non_multipath_scsi_block_devices(block_devices)
        return any([self.volume_name == device.get_vendor().get_volume_name() \
#                    for device in mp_devices + non_mp_devices])
                     for device in block_devices])

class InfinidatVolumeDoesNotExist(InfinidatVolumeExists):
    """A predicate that checks if an Infinidat volume does not exist"""
    def __call__(self):
        return not super(InfinidatVolumeDoesNotExist, self).__call__()
