from contextlib import contextmanager

from ..base import StorageModel, scsi, multipath
from .. import StorageModelFindError
from infi.pyutils.lazy import cached_method

from .sysfs import Sysfs

class LinuxSCSIDeviceMixin(object):
    @contextmanager
    def asi_context(self):
        import os
        from infi.asi.unix import OSFile
        from infi.asi import create_platform_command_executer

        handle = OSFile(os.open(self.get_scsi_access_path(), os.O_RDWR))
        executer = create_platform_command_executer(handle)
        try:
            yield executer
        finally:
            handle.close()

    @cached_method
    def get_hctl(self):
        return self.sysfs_device.get_hctl()

    @cached_method
    def get_display_name(self):
        return self.sysfs_device.get_block_device_name()

    @cached_method
    def get_block_access_path(self):
        return "/dev/%s" % self.sysfs_device.get_block_device_name()

    @cached_method
    def get_scsi_access_path(self):
        return "/dev/%s" % self.sysfs_device.get_scsi_generic_device_name()

    @cached_method
    def get_unix_block_devno(self):
        return self.sysfs_device.get_block_devno()

    @cached_method
    def get_linux_scsi_generic_devno(self):
        return self.sysfs_device.get_scsi_generic_devno()

    # This is either in SCSIBlockDevice or in SCSIStorageController, so we put this here anyhow.
    @cached_method
    def get_vendor(self):
        return self.sysfs_device.get_vendor()

class LinuxSCSIBlockDevice(LinuxSCSIDeviceMixin, scsi.SCSIBlockDevice):
    def __init__(self, sysfs_device):
        super(LinuxSCSIBlockDevice, self).__init__()
        self.sysfs_device = sysfs_device

    @cached_method
    def get_size_in_bytes(self):
        return self.sysfs_device.get_size_in_bytes()

class LinuxSCSIStorageController(LinuxSCSIDeviceMixin, scsi.SCSIStorageController):
    def __init__(self, sysfs_device):
        super(LinuxSCSIStorageController, self).__init__()
        self.sysfs_device = sysfs_device

class LinuxSCSIModel(scsi.SCSIModel):
    def __init__(self):
        self.sysfs = Sysfs()

    @cached_method
    def get_all_scsi_block_devices(self):
        return [ LinuxSCSIBlockDevice(sysfs_disk) for sysfs_disk in self.sysfs.get_all_scsi_disks() ]

    @cached_method
    def get_all_storage_controller_devices(self):
        return [ LinuxSCSIStorageController(sysfs_dev) for sysfs_dev in self.sysfs.get_all_scsi_storage_controllers() ]

    def find_scsi_block_device_by_block_devno(self, devno):
        devices = [ dev for dev in self.get_all_scsi_block_devices() if dev.get_unix_block_devno() == devno ]
        if len(devices) != 1:
            raise StorageModelFindError("%d SCSI block devices found with devno=%s" % (len(devices), devno))
        return devices[0]

class LinuxNativeMultipathModel(multipath.NativeMultipathModel):
    @cached_method
    def get_all_multipath_devices(self):
        # TODO: implement
        raise NotImplementedError()

class LinuxStorageModel(StorageModel):
    def _create_scsi_model(self):
        return LinuxSCSIModel()

    def _create_native_multipath_model(self):
        return LinuxNativeMultipathModel()

    def initiate_rescan(self):
        # TODO: implement
        raise NotImplementedError()
