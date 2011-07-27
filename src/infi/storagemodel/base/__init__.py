
class SCSIDevice(object):

    def with_asi_context(self):
        pass

    @property
    def hctl(self):
        # OS-specific
        raise NotImplementedError

    @property
    def scsi_serial(self):
        # Returns the SCSI serial of the device or an empty string ("") if not available
        # TODO is it worth a while to have a base implemtation that gets it from page80 inquiry?
        raise NotImplementedError

    @property
    def scsi_standard_inquiry(self):
        # base implementation
        raise NotImplementedError

    @property
    def scsi_inquiry_pages(self):
        # return an immutable dict-like object.
        # lazy fetch the list of supported pages. each __getitem__ will be then fetched.
        # e.g. scsi_inquiry_pages[0x80]
        # base implementation
        pass

    @property
    def display_name(self):
        # platform implementation
        raise NotImplementedError

    @property
    def vendor_specific_mixin(self):
        """ Returns a mixin object from the factory based on the device's vid, pid
        If there is no mixing interface available, this property returns None
        """
        from ..vendor_specific import VendorSpecificFactory
        VendorSpecificFactory().create_mixin_object(self)
        # TODO vendor factory is NOT!!! platform specific
        # dev.vendor_specific_mixin.infi_volume
        pass

    @property
    def connectivity_mixin(self):
        """ Returns a mixin instance of this object and a connectivity interface
        """
        # TODO connectivity factory, is it platform specific? for fiberchannel - yes, for iscsi???
        # Return either an iSCSIConnectivityInfo or FiberChannelConnectivityInfo
        from ..connectivity import ConnectivityFactory
        return ConnectivityFactory.create_mixin_object(self)

class SCSIBlockDevice(SCSIDevice):
    @property
    def size_in_bytes(self):
        # platform implementation
        raise NotImplementedError

class SCSIStorageController(SCSIDevice):
    pass

class ScsiModel(object):
    def __init__(self):
        super(ScsiModel, self).__init__()


    def refresh_scsi_block_devices(self):
        """
        Clears the current device list so next time we'll read the device list from the OS.
        """
        raise NotImplementedError

    def get_all_scsi_block_devices(self):
        """
        Returns all SCSI block devices
          - Windows: Enumerate Disk Drives, Collecting SCSI devices that can work with SCSI_PASS_THROUGH
          - Linux:   we scan all the sd* (/sys/class/scsi_disk/*)
           - 
        SCSIBlockDevice:
          - pointer to sg
          - pointer to sd
        """
        raise NotImplementedError

    def find_scsi_block_device_by_devno(self, devno):
        # TODO this is not cross-platform, should it be in here?
        raise NotImplementedError

    def find_scsi_block_device_by_path(self, path):
        raise NotImplementedError

    def find_scsi_block_device_by_hctl(self, hctl):
        raise NotImplementedError

    def filter_vendor_specific_devices(self, devices, vendor_mixin):
        return filter(lambda x: isinstance(x.vendor_specific_mixin, vendor_mixin), devices)

    def get_all_storage_controller_devices(self):
        """
        Returns a list of SCSIStorageController/whatever objects.
        """
        raise NotImplementedError

    def rescan_and_wait_for(self, hctl_map, timeout_in_seconds=None):
        """
        Rescan devices and wait for user-defined changes. Each key is an HCTL object and each value is True/False.
        True means the device should be mapped, False means that it should be unmapped.
        """
        raise NotImplementedError

class MultipathFrameworkModel(object):
    def get_devices(self):
        """ returns all multipath devices claimed by this framework
        """
        raise NotImplementedError

    def pop_non_multipath_scsi_block_devices(self, scsi_block_devices):
        """ returns items from the list that are not part of multipath devices claimed by this framework
        """
        raise NotImplementedError

    def filter_vendor_specific_devices(self, devices, vendor_mixin):
        return filter(lambda x: isinstance(x.vendor_specific_mixin, vendor_mixin), devices)

class NativeMultipathModel(MultipathFrameworkModel):
    pass
