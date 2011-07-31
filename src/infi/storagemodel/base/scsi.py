
from ..utils import cached_property, cached_method
from contextlib import contextmanager

from .inquiry import InquiryInformationMixin

class SCSIDevice(InquiryInformationMixin, object):
    @cached_property
    def connectivity(self):
        """returns either an FCConnnectivity object or ISCSIConnectivity object"""
        from ..connectivity import ConnectivityFactory
        return ConnectivityFactory.get_by_device_with_hctl(self)

    #############################
    # Platform Specific Methods #
    #############################

    @contextmanager
    def asi_context(self):
        # platform implementation
        raise NotImplementedError()

    @cached_property
    def hctl(self):
        """returns a HCTL object"""
        # platform implementation
        raise NotImplementedError()

    @cached_property
    def display_name(self):
        """returns a friendly device name.
        In Windows, its PHYSICALDRIVE%d, in linux, its sdX.
        """
        # platform implementation
        raise NotImplementedError

    @cached_property
    def block_access_path(self):
        """returns a string path for the device
        In Windows, its something under globalroot
        In linux, its /dev/sdX"""
        # platform implementation
        raise NotImplementedError

    @cached_property
    def scsi_access_path(self):
        """returns a string path for the device
        In Windows, its something under globalroot like block_device_path
        In linux, its /dev/sgX"""
        # platform implementation        
        raise NotImplementedError

class SCSIBlockDevice(SCSIDevice):
    @cached_property
    def vendor(self):
        """ Returns a vendor-specific implementation from the factory based on the device's SCSI vid and pid"""
        from ..vendor import VendorFactory
        return VendorFactory.create_block_by_vid_pid(self.scsi_vid_pid, self)

    #############################
    # Platform Specific Methods #
    #############################

    @cached_property
    def size_in_bytes(self):
        # platform implementation
        raise NotImplementedError

class SCSIStorageController(SCSIDevice):
    @cached_property
    def vendor(self):
        """ Returns a vendor-specific implementation from the factory based on the device's SCSI vid and pid"""
        from ..vendor import VendorFactory
        return VendorFactory.create_controller_by_vid_pid(self.scsi_vid_pid, self)

class SCSIModel(object):
    def find_scsi_block_device_by_block_access_path(self, path):
        """return a SCSIBlockDevice object that matches the given path. raises KeyError if no such device is found"""
        devices_dict = dict([(device.block_access_path, device) for device in self.get_all_scsi_block_devices()])
        return devices_dict[path]

    def find_scsi_block_device_by_scsi_access_path(self, path):
        """return a SCSIBlockDevice object that matches the given path. raises KeyError if no such device is found"""
        devices_dict = dict([(device.scsi_access_path, device) for device in self.get_all_scsi_block_devices()])
        return devices_dict[path]

    def find_scsi_block_device_by_hctl(self, hctl):
        """return a SCSIBlockDevice object that matches the given hctl. raises KeyError if no such device is found"""
        devices_dict = dict([(device.hctl, device) for device in self.get_all_scsi_block_devices()])
        return devices_dict[hctl]

    def filter_vendor_specific_devices(self, devices, vid_pid_tuple):
        """returns only the items from the devices list that are of the specific type"""
        return filter(lambda x: x.scsi_vid_pid == vid_pid_tuple, devices)

    #############################
    # Platform Specific Methods #
    #############################

    @cached_method
    def get_all_scsi_block_devices(self):
        """
        Returns all SCSI block devices
          - Windows: Enumerate Disk Drives, Collecting SCSI devices that can work with SCSI_PASS_THROUGH.
               They can be either be multipath or non-multipath devices.
          - Linux:   we scan all the sd* (/sys/class/scsi_disk/*)
           - 
        """
        # platform implementation
        raise NotImplementedError

    @cached_method
    def get_all_storage_controller_devices(self):
        """ Returns a list of SCSIStorageController objects.
        """
        # platform implementation
        raise NotImplementedError

    def rescan_and_wait_for(self, hctl_map, timeout_in_seconds=None):
        # TODO: I discussed this with rotem, he wants a different thing:
        # In this use-cas he's mapping a volume to volume onto a lun to an initiator port, and he wants to wait for
        # the mapping to wait. He wants to pass a list of (initiator_port, target_port, lun) and have us wait on these.
        # if initiator_port is None, we shall wait on each initiator_port we are aware of.
        # this is true for fiberchannel.
        # for iscsi the tuple is made of (initiator_iqn, initiator_ip, target_iqn, target_ip, lun).
        """ Rescan devices and wait for user-defined changes. Each key is an HCTL object and each value is True/False.
        True means the device should be mapped, False means that it should be unmapped.
        """
        # platform implementation
        raise NotImplementedError
