
from infi.pyutils.lazy import cached_method
from . import VendorMultipathDevice, VendorSCSIBlockDevice, VendorSCSIStorageController

class InfiniBoxMixin(object):
    @cached_method
    def get_box_ipv4_address(self):
        """:returns: the management IPv4 address of the InfiniBox
        :rtype: string"""
        from infi.asi.cdb.inquiry.vpd_pages.device_identification.designators import SCSINameDesignator
        device_identification_page = self.get_scsi_inquiry_pages()[0x83]
        for designator in device_identification_page.designators_list:
            if isinstance(designator, SCSINameDesignator) and designator.scsi_name_string.startswith("ip"):
                return designator.scsi_name_string.split("=")[1]

    @cached_method
    def get_host_name(self):
        """:returns: the host name within the InfiniBox
        :rtype: string"""
        from infi.asi.cdb.inquiry.vpd_pages.device_identification.designators import SCSINameDesignator
        device_identification_page = self.get_scsi_inquiry_pages()[0x83]
        for designator in device_identification_page.designators_list:
            if isinstance(designator, SCSINameDesignator) and designator.scsi_name_string.startswith("host"):
                return designator.scsi_name_string.split("=")[1]

class InfiniBoxVolumeMixin(object):
    @cached_method
    def get_volume_name(self):
        """:returns: the volume name within the InfiniBox
        :rtype: string"""
        from infi.asi.cdb.inquiry.vpd_pages.device_identification.designators import SCSINameDesignator
        device_identification_page = self.get_scsi_inquiry_pages()[0x83]
        for designator in device_identification_page.designators_list:
            if isinstance(designator, SCSINameDesignator) and designator.scsi_name_string.startswith("vol"):
                return designator.scsi_name_string.split("=")[1]

class block_class(InfiniBoxMixin, VendorSCSIBlockDevice, InfiniBoxVolumeMixin):
    pass

class controller_class(InfiniBoxMixin, VendorSCSIStorageController):
    pass

class multipath_class(InfiniBoxMixin, VendorMultipathDevice, InfiniBoxVolumeMixin):
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
        mp_devices = mpath.filter_vendor_specific_devices(mpath.get_all_multipath_devices(), vid_pid)
        non_mp_devices = mpath.filter_non_multipath_scsi_block_devices(block_devices)
        return any([self.volume_name in device.get_scsi_inquiry_pages()[0x83].page_data \
                    for device in mp_devices + non_mp_devices])
