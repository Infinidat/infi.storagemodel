
class SCSIDevice(object):
    def with_asi_context(self):
        pass

    @property
    def hctl(self):
        # OS-specific
        raise NotImplementedError

    @property
    def scsi_serial_number(self):
        """ Returns the SCSI serial of the device or an empty string ("") if not available
        """
        # TODO is it worth a while to have a base implemtation that gets it from page80 inquiry?
        raise NotImplementedError

    @property
    def scsi_standard_inquiry(self):
        # base implementation
        raise NotImplementedError

    @property
    def scsi_inquiry_pages(self):
        """ return an immutable dict-like object of available inquiry pages from this device
        """
        # lazy fetch the list of supported pages. each __getitem__ will be then fetched.
        # e.g. scsi_inquiry_pages[0x80]
        # base implementation
        pass

    @property
    def display_name(self):
        """ returns a friendly device name.
        In Windows, its PHYSICALDRIVE%d, in linux, its sdX.
        """
        # platform implementation
        raise NotImplementedError

    @property
    def device_path(self):
        """ returns a path for the device
        In Windows, its something under globalroot
        In linux, its /dev/sgx
        """
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
    def refresh_scsi_block_devices(self):
        """
        Clears the current device list so next time we'll read the device list from the OS.
        """
        raise NotImplementedError

    def get_all_scsi_block_devices(self):
        """
        Returns all SCSI block devices
          - Windows: Enumerate Disk Drives, Collecting SCSI devices that can work with SCSI_PASS_THROUGH.
               They can be either be multipath or non-multipath devices.
          - Linux:   we scan all the sd* (/sys/class/scsi_disk/*)
           - 
        """
        raise NotImplementedError

    def find_scsi_block_device_by_devno(self, devno):
        """ raises KeyError if not found. devno is type of str.
        on linux: by major/minor
        on windows: by number of physicaldrive
        """
        # TODO this is not cross-platform, should it be in here?
        raise NotImplementedError

    def find_scsi_block_device_by_path(self, path):
        """ raises KeyError if not found
        """
        # platform specific implementation. if there are several paths (sg, sd), it will search both
        raise NotImplementedError

    def find_scsi_block_device_by_hctl(self, hctl):
        """ raises KeyError if not found
        """
        raise NotImplementedError

    def filter_vendor_specific_devices(self, devices, vendor_mixin):
        """ returns only the items from the devices list that are of the specific type
        """
        return filter(lambda x: isinstance(x.vendor_specific_mixin, vendor_mixin), devices)

    def get_all_storage_controller_devices(self):
        """ Returns a list of SCSIStorageController objects.
        """
        raise NotImplementedError

    def rescan_and_wait_for(self, hctl_map, timeout_in_seconds=None):
        """ Rescan devices and wait for user-defined changes. Each key is an HCTL object and each value is True/False.
        True means the device should be mapped, False means that it should be unmapped.
        """
        raise NotImplementedError

class MultipathFrameworkModel(object):
    def get_devices(self):
        """ returns all multipath devices claimed by this framework
        """
        raise NotImplementedError

    def filter_non_multipath_scsi_block_devices(self, scsi_block_devices):
        """ returns items from the list that are not part of multipath devices claimed by this framework
        """
        raise NotImplementedError

    def filter_vendor_specific_devices(self, devices, vendor_mixin):
        """ returns only the items from the devices list that are of the specific type
        """
        return filter(lambda x: isinstance(x.vendor_specific_mixin, vendor_mixin), devices)

class NativeMultipathModel(MultipathFrameworkModel):
    pass

class MultipathDevice(object):
    @property
    def device_path(self):
        """ linux: /dev/dm-X
        windows: mpiodisk%d
        """
        pass

    @property
    def display_name(self):
        """ linux: mpathX
        windows: physicaldrive
        """
        pass

    def with_asi_context(self):
        """ returns an asi object to the mulipath device itself
        """
        # TODO: do we get a context to one of the single-path devices or to the mpath device
        pass

    @property
    def scsi_serial_number(self):
        # TODO is it worth a while to have a base implemtation that gets it from page80 inquiry?
        raise NotImplementedError

    @property
    def scsi_standard_inquiry(self):
        """ there is no gurantee on which path this io goes on
        """
        # base implementation
        raise NotImplementedError

    @property
    def scsi_inquiry_pages(self):
        """ no warranty that all pages will be fetched from each path
        """
        # lazy fetch the list of supported pages. each __getitem__ will be then fetched.
        # e.g. scsi_inquiry_pages[0x80]
        # base implementation
        pass

    @property
    def size_in_bytes(self):
        # platform implementation
        raise NotImplementedError

    @property
    def paths(self):
        pass


    @property
    def policy(self):
        """ 'failover only', 'round robin', 'weighted round robin', 'least queue depth', 'least blocks'
        not all policies are supported on all platforms
        """

    @policy.settr
    def policy(self, new_policy, paths):
        """
        linux: 
            failover only: group per path
            round-robin: all paths in one group, we ignore path states, weights
            weighted-paths: all paths in one group, allow weights
            round-robin with subset: not supported
            least queue depth: all paths in one group, selector is queue-length, not supported on all all distros
            least blocks: all paths in hour group, select is service-time, not supported on all distros
        windows: 
            round-robin with subset: not supported
            on invalid policy, ValueError is raised
            """
        pass

class Path(object):
    @property
    def path_id(self):
        """ sdX on linux, PathId on Windows
        """
        pass

    @property
    def hctl(self):
        pass

    @property
    def state(self):
        """ active, inactive, disconnected
        """
        pass

    @property
    def weight(self):
        pass
