
from .. import base
from ..utils import cached_method, cached_property, clear_cache
from infi.storagemodel.base import SCSIBlockDevice, SCSIDevice
from contextlib import contextmanager

class WindowsSCSIDevice(SCSIDevice):
    def __init__(self, device_object):
        self._device_object = device_object

    @cached_property
    def scsi_vendor_id(self):
        # a faster implemntation on windows
        return self._device_object.hardware_ids[-2][0:8].replace('_', '')

    @cached_property
    def scsi_product_id(self):
        # a faster implementation on windows
        return self._device_object.hardware_ids[-2][8:24].replace('_', '')

    @contextmanager
    def asi_context(self):
        from infi.asi.win32 import OSFile
        from infi.asi import create_platform_command_executer
        handle = OSFile(self.scsi_access_path)
        executer = create_platform_command_executer(handle)
        try:
            yield executer
        finally:
            handle.close()

    @cached_property
    def hctl(self):
        from ..dtypes import HCTL
        address = self.ioctl_interface.scsi_get_address()
        return HCTL(address.PortNumber, address.PathId, address.TargetId, address.Lun)

    @cached_property
    def block_access_path(self):
        return self._device_object.psuedo_device_object

    @cached_property
    def scsi_access_path(self):
        return SCSIDevice.scsi_access_path(self)

    @cached_property
    def ioctl_interface(self):
        from infi.devicemanager.ioctl import DeviceIoControl
        return DeviceIoControl(self.scsi_access_path)

    @cached_property
    def display_name(self):
        return self.scsi_access_path.split('\\')[-1]

class WindowsSCSIBlockDevice(WindowsSCSIDevice, SCSIBlockDevice):
    @cached_property
    def physical_drive_number(self):
        """returns the drive number of the disk.
        if the disk is hidden (i.e. part of MPIODisk), it returns -1
        """
        number = self.ioctl_interface.storage_get_device_number().DeviceNumber
        return -1 if number == 0xffffffff else number

    @cached_property
    def display_name(self):
        return "PHYSICALDRIVE%s" % self.physical_drive_number

class WindowsSCSIStorageController(base.SCSIStorageController, WindowsSCSIDevice):
    def display_name(self):
        return SCSIDevice.display_name(self)

class WindowsSCSIModel(base.ScsiModel):
    @cached_method
    def device_manager(self):
        from infi.devicemanager import DeviceManager
        return DeviceManager()

    @cached_method
    def get_all_scsi_block_devices(self):
        return filter(lambda disk: disk.physical_drive_number != -1,
                      [WindowsSCSIBlockDevice(device) for device in self.device_manager.disk_drives])

    @cached_method
    def get_all_storage_controller_devices(self):
        from infi.devicemanager.setupapi.constants import SYSTEM_DEVICE_GUID_STRING
        # Stoage controllers are listed under the SCSI Adapters and their CLASSGUID is this
        # Unless there are some other SCSI devices that have this GUID (afaik there aren't)
        # this is good enough
        return filter(lambda device: device.class_guid == SYSTEM_DEVICE_GUID_STRING,
                      [WindowsSCSIStorageController(device) for device in self.device_manager.scsi_devices])

class WindowsNativeMultipathModel(base.NativeMultipathModel):
    pass
