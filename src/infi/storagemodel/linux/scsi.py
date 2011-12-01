from contextlib import contextmanager
from ..base import scsi
from ..errors import StorageModelFindError
from infi.pyutils.lazy import cached_method
from .block import LinuxBlockDeviceMixin

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
    def get_scsi_access_path(self):
        return "/dev/%s" % self.sysfs_device.get_scsi_generic_device_name()

    @cached_method
    def get_linux_scsi_generic_devno(self):
        return self.sysfs_device.get_scsi_generic_devno()

class LinuxSCSIBlockDeviceMixin(LinuxSCSIDeviceMixin, LinuxBlockDeviceMixin):
    pass

class LinuxSCSIBlockDevice(LinuxSCSIBlockDeviceMixin, scsi.SCSIBlockDevice):
    def __init__(self, sysfs_device):
        super(LinuxSCSIBlockDevice, self).__init__()
        self.sysfs_device = sysfs_device

    @cached_method
    def get_display_name(self):
        return self.sysfs_device.get_block_device_name()

class LinuxSCSIStorageController(LinuxSCSIDeviceMixin, scsi.SCSIStorageController):
    # pylint: disable=W0223
    # This methods below are overriden by platform-specific implementations

    def __init__(self, sysfs_device):
        super(LinuxSCSIStorageController, self).__init__()
        self.sysfs_device = sysfs_device

    @cached_method
    def get_display_name(self):
        return self.sysfs_device.get_scsi_generic_device_name()

class LinuxSCSIModel(scsi.SCSIModel):
    def __init__(self, sysfs):
        self.sysfs = sysfs

    @cached_method
    def get_all_scsi_block_devices(self):
        return [ LinuxSCSIBlockDevice(sysfs_disk) for sysfs_disk in self.sysfs.get_all_scsi_disks() ]

    @cached_method
    def get_all_storage_controller_devices(self):
        return [ LinuxSCSIStorageController(sysfs_dev) for sysfs_dev in self.sysfs.get_all_scsi_storage_controllers() ]

    def find_scsi_block_device_by_block_devno(self, devno):
        devices = [ dev for dev in self.get_all_scsi_block_devices() if dev.get_unix_block_devno() == devno ]
        if len(devices) != 1:
            raise StorageModelFindError("%d SCSI block devices found with devno=%s" % (len(devices), devno)) # pylint: disable=W0710
        return devices[0]
