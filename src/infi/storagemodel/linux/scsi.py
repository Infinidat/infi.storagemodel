from contextlib import contextmanager
from ..base import scsi, gevent_wrapper
from ..errors import StorageModelFindError
from infi.pyutils.lazy import cached_method
from .block import LinuxBlockDeviceMixin
from infi.storagemodel.base.scsi import SCSIBlockDevice
from infi.storagemodel.base.inquiry import InquiryInformationMixin
from infi.exceptools import chain
from infi.pyutils.decorators import wraps
from .rescan_scsi_bus.getters import is_sg_module_loaded
from .rescan_scsi_bus.scsi import execute_modprobe_sg
from logging import getLogger


MS = 1000
SG_TIMEOUT_IN_SEC = 3
SG_TIMEOUT_IN_MS = SG_TIMEOUT_IN_SEC * MS


logger = getLogger(__name__)


class LinuxSCSIDeviceMixin(object):
    @contextmanager
    def asi_context(self):
        from infi.asi import create_platform_command_executer, create_os_file

        handle = create_os_file(self.get_scsi_access_path())
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
        try:
            return self.sysfs_device.get_vendor().strip()
        except IOError:
            logger.exception("failed to get vendor from sysfs, trying to send a CDB")
            return InquiryInformationMixin.get_scsi_vendor_id(self)

    @cached_method
    def get_scsi_revision(self):
        try:
            return self.sysfs_device.get_revision().strip()
        except IOError:
            logger.exception("failed to get scsi revision from sysfs, trying to send a CDB")
            return InquiryInformationMixin.get_scsi_revision(self)

    @cached_method
    def get_scsi_product_id(self):
        try:
            return self.sysfs_device.get_model().strip()
        except IOError:
            logger.exception("failed to get production from sysfs, trying to send a CDB")
            return InquiryInformationMixin.get_scsi_product_id(self)


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
        # our need the 'sg' module, which is no longer loaded during system boot on redhat-7.1
        if not is_sg_module_loaded():
            execute_modprobe_sg()

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
