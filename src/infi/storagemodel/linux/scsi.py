from contextlib import contextmanager
from ..base import scsi, gevent_wrapper
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
        executer.call = gevent_wrapper.defer(executer.call)
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

    @cached_method
    def get_scsi_vendor_id(self):
        return self.sysfs_device.get_vendor().strip()

    @cached_method
    def get_scsi_revision(self):
        return self.sysfs_device.get_revision().strip()


    @cached_method
    def get_scsi_product_id(self):
        return self.sysfs_device.get_model().strip()


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


class LinuxSCSIModel(scsi.SCSIModel):
    def __init__(self, sysfs):
        self.sysfs = sysfs

    @cached_method
    def get_all_scsi_block_devices(self):
        devices = [item for item in self.get_all_linux_scsi_generic_disk_devices() if
                   isinstance(item, SCSIBlockDevice)]
        return devices

    @cached_method
    def get_all_storage_controller_devices(self):
        return [LinuxSCSIStorageController(sysfs_dev) for sysfs_dev in self.sysfs.get_all_scsi_storage_controllers()]

    @cached_method
    def get_all_enclosure_devices(self):
        return [LinuxSCSIEnclosure(sysfs_dev) for sysfs_dev in self.sysfs.get_all_enclosures()]

    @cached_method
    def get_all_linux_scsi_generic_disk_devices(self):
        """Linux specific: returns a list of ScsiDisk objects that do not rely on SD"""
        from .sysfs import SysfsSDDisk
        return [LinuxSCSIBlockDevice(disk) if isinstance(disk, SysfsSDDisk) else LinuxSCSIGenericDevice(disk)
                for disk in self.sysfs.get_all_sg_disks()]
