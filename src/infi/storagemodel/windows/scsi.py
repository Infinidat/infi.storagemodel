
from infi.pyutils.lazy import cached_method
from ..base import scsi
from .device_mixin import WindowsDeviceMixin, WindowsDiskDeviceMixin
from .device_helpers import is_disk_drive_managed_by_windows_mpio, safe_get_physical_drive_number
from .device_helpers import is_disk_visible_in_device_manager, is_device_installed

# pylint: disable=W0212,E1002

class WindowsSCSIDevice(WindowsDeviceMixin, scsi.SCSIDevice):
    def __init__(self, device_object):
        super(WindowsSCSIDevice, self).__init__()
        self._device_object = device_object

    @cached_method
    def get_scsi_access_path(self):
        return self.get_pdo()

    @cached_method
    def get_display_name(self):
        return self.get_scsi_access_path().split('\\')[-1]

class WindowsSCSIBlockDevice(WindowsDiskDeviceMixin, WindowsSCSIDevice, scsi.SCSIBlockDevice):
    pass

class WindowsSCSIStorageController(WindowsSCSIDevice, scsi.SCSIStorageController):
    pass

class WindowsSCSIModel(scsi.SCSIModel):
    @cached_method
    def get_device_manager(self):
        from infi.devicemanager import DeviceManager
        return DeviceManager()

    def _iter(self):
        for disk_drive in self.get_device_manager().disk_drives:
            if is_disk_drive_managed_by_windows_mpio(disk_drive):
                continue
            if not is_device_installed(disk_drive):
                continue
            if not is_disk_visible_in_device_manager(disk_drive):
                continue
            device = WindowsSCSIBlockDevice(disk_drive)
            if safe_get_physical_drive_number(device) == -1:
                continue
            yield WindowsSCSIBlockDevice(disk_drive)

    @cached_method
    def get_all_scsi_block_devices(self):
        return list(self._iter())

    @cached_method
    def get_all_storage_controller_devices(self):
        controller_devices = []
        for scsi_device in self.get_device_manager().scsi_devices:
            if is_device_installed(scsi_device) and u'ScsiArray' in scsi_device.hardware_ids:
                controller_devices.append(WindowsSCSIStorageController(scsi_device))
        return controller_devices
