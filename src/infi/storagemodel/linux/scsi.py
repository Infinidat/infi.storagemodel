from contextlib import contextmanager
from ..base import scsi
from ..errors import StorageModelFindError, DeviceDisappeared
from infi.pyutils.lazy import cached_method
from .block import LinuxBlockDeviceMixin
from infi.storagemodel.base.scsi import SCSIBlockDevice
from infi.exceptools import chain
from infi.pyutils.decorators import wraps

MS = 1000
SG_TIMEOUT_IN_SEC = 3
SG_TIMEOUT_IN_MS = SG_TIMEOUT_IN_SEC * MS


class LinuxSCSIDeviceMixin(object):
    @contextmanager
    def asi_context(self):
        import os
        from infi.asi.unix import OSFile
        from infi.asi import create_platform_command_executer

        handle = OSFile(os.open(self.get_scsi_access_path(), os.O_RDWR))
        executer = create_platform_command_executer(handle, timeout=SG_TIMEOUT_IN_MS)
        try:
            yield executer
        finally:
            handle.close()

    @cached_method
    def get_hctl(self):
        return self.sysfs_device.get_hctl()

    @cached_method
    def get_sas_address(self):
        return self.sysfs_device.get_sas_address()

    @cached_method
    def get_scsi_access_path(self):
        return "/dev/%s" % self.sysfs_device.get_scsi_generic_device_name()

    @cached_method
    def get_linux_scsi_generic_devno(self):
        return self.sysfs_device.get_scsi_generic_devno()


class LinuxSCSIBlockDeviceMixin(LinuxSCSIDeviceMixin, LinuxBlockDeviceMixin):
    pass


class LinuxSCSIGenericDevice(LinuxSCSIDeviceMixin, scsi.SCSIDevice):
    def __init__(self, sysfs_device):
        super(LinuxSCSIGenericDevice, self).__init__()
        self.sysfs_device = sysfs_device

    @cached_method
    def get_display_name(self):
        return self.sysfs_device.get_scsi_generic_device_name()


class LinuxSCSIBlockDevice(LinuxSCSIBlockDeviceMixin, scsi.SCSIBlockDevice):
    def __init__(self, sysfs_device):
        super(LinuxSCSIBlockDevice, self).__init__()
        self.sysfs_device = sysfs_device

    @cached_method
    def get_display_name(self):
        return self.sysfs_device.get_block_device_name()


class LinuxSCSIStorageController(LinuxSCSIDeviceMixin, scsi.SCSIStorageController):
    def __init__(self, sysfs_device):
        super(LinuxSCSIStorageController, self).__init__()
        self.sysfs_device = sysfs_device

    @cached_method
    def get_display_name(self):
        return self.sysfs_device.get_scsi_generic_device_name()


class LinuxSCSIEnclosure(LinuxSCSIDeviceMixin, scsi.SCSIEnclosure):
    def __init__(self, sysfs_device):
        super(LinuxSCSIEnclosure, self).__init__()
        self.sysfs_device = sysfs_device

    @cached_method
    def get_display_name(self):
        return self.sysfs_device.get_scsi_generic_device_name()

    def get_slot_occupant_hctl(self, slot):
        return self.sysfs_device.find_hctl_by_slot(slot)


def device_disappered(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (IOError, OSError):
            raise chain(DeviceDisappeared())
    return wrapper


class LinuxSCSIModel(scsi.SCSIModel):
    def __init__(self, sysfs):
        self.sysfs = sysfs

    def _raise_exception_if_sd_devices_are_missing(self, devices):
        for disk in [disk for disk in devices if not isinstance(disk, SCSIBlockDevice)]:
            raise DeviceDisappeared("No block dev names for {}".format(disk.get_scsi_access_path()))

    @cached_method
    def get_all_scsi_block_devices(self):
        devices = self.get_all_linux_scsi_generic_disk_devices()
        self._raise_exception_if_sd_devices_are_missing(devices)
        return devices

    @device_disappered
    @cached_method
    def get_all_storage_controller_devices(self):
        return [LinuxSCSIStorageController(sysfs_dev) for sysfs_dev in self.sysfs.get_all_scsi_storage_controllers()]

    @device_disappered
    @cached_method
    def get_all_enclosure_devices(self):
        return [LinuxSCSIEnclosure(sysfs_dev) for sysfs_dev in self.sysfs.get_all_enclosures()]

    def find_scsi_block_device_by_block_devno(self, devno):
        devices = [dev for dev in self.get_all_scsi_block_devices() if dev.get_unix_block_devno() == devno]
        if len(devices) != 1:
            raise StorageModelFindError("%d SCSI block devices found with devno=%s" % (len(devices), devno))  # pylint: disable=W0710
        return devices[0]

    @device_disappered
    @cached_method
    def get_all_linux_scsi_generic_disk_devices(self):
        """Linux specific: returns a list of ScsiDisk objects that do not rely on SD"""
        from .sysfs import SysfsSDDisk
        return [LinuxSCSIBlockDevice(disk) if isinstance(disk, SysfsSDDisk) else LinuxSCSIGenericDevice(disk)
                for disk in self.sysfs.get_all_sg_disks()]
