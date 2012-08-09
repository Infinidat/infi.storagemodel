
from infi.pyutils.lazy import cached_method
from ..base import scsi
from .device_mixin import WindowsDeviceMixin, WindowsDiskDeviceMixin

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
    @cached_method
    def get_block_access_path(self):
        return self.get_pdo()

class WindowsSCSIStorageController(WindowsSCSIDevice, scsi.SCSIStorageController):
    pass

class WindowsSCSIModel(scsi.SCSIModel):
    @cached_method
    def get_device_manager(self):
        from infi.devicemanager import DeviceManager
        return DeviceManager()

    @cached_method
    def get_all_scsi_block_devices(self):
        from .native_multipath import MPIO_BUS_DRIVER_INSTANCE_ID
        return filter(lambda disk: disk.get_physical_drive_number() != -1,
                      map(lambda device: WindowsSCSIBlockDevice(device),
                          filter(lambda disk: disk.parent._instance_id.lower() != MPIO_BUS_DRIVER_INSTANCE_ID and not disk.is_hidden(),
                                 self.get_device_manager().disk_drives)))

    @cached_method
    def get_all_storage_controller_devices(self):
        from infi.devicemanager.setupapi.constants import SYSTEM_DEVICE_GUID_STRING
        return filter(lambda device: u'ScsiArray' in device._device_object.hardware_ids,
                      [WindowsSCSIStorageController(device) for device in self.get_device_manager().scsi_devices])
