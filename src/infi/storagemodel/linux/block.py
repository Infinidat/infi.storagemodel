from infi.pyutils.lazy import cached_method


class LinuxBlockDeviceMixin(object):
    NAA_DESIGNATOR_TYPE = 0x03
    LOGICAL_UNIT_ASSOCIATION = 0x00

    @cached_method
    def get_block_access_path(self):
        return "/dev/%s" % self.sysfs_device.get_block_device_name()

    @cached_method
    def get_unix_block_devno(self):
        return self.sysfs_device.get_block_devno()

    @cached_method
    def get_size_in_bytes(self):
        return self.sysfs_device.get_size_in_bytes()

    @cached_method
    def get_device_identification_page(self):
        from infi.asi.cdb.inquiry.vpd_pages import INQUIRY_PAGE_DEVICE_IDENTIFICATION
        try:
            device_identification_page = self.get_scsi_inquiry_pages()[INQUIRY_PAGE_DEVICE_IDENTIFICATION]
            return device_identification_page
        except KeyError:    # Device does not support inquiry page 0x83
            return None

    @cached_method
    def get_wwid(self):
        import binascii
        from infi.asi.cdb.inquiry.vpd_pages.designators import NAA_Descriptor
        device_identification_page = self.get_device_identification_page()
        if not device_identification_page:
            return None
        for designator in device_identification_page.designators_list:
            if not isinstance(designator, NAA_Descriptor):
                continue
            if designator.designator_type == self.NAA_DESIGNATOR_TYPE and \
               designator.association == self.LOGICAL_UNIT_ASSOCIATION:
                return '3{}'.format(binascii.hexlify(designator.pack())[8:].decode('ASCII'))
        return None
