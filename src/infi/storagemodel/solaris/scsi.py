from contextlib import contextmanager
from ..base import scsi, gevent_wrapper
from infi.pyutils.lazy import cached_method
from infi.storagemodel.base.scsi import SCSIBlockDevice, SCSIStorageController, SCSIModel

QUERY_TIMEOUT = 3 # 3 seconds

class SolarisSCSIDeviceMixin(object):
    @contextmanager
    def asi_context(self):
        import os
        from infi.asi.unix import OSFile
        from infi.asi import create_platform_command_executer

        handle = OSFile(os.open(self.get_scsi_access_path(), os.O_RDWR))
        executer = create_platform_command_executer(handle, timeout=QUERY_TIMEOUT)
        executer.call = gevent_wrapper.defer(executer.call)
        try:
            yield executer
        finally:
            handle.close()

    @cached_method
    def get_hctl(self):
        return self._device_manager_obj.get_hctl()

    @cached_method
    def get_scsi_access_path(self):
        return self._device_manager_obj.get_scsi_access_path()

    @cached_method
    def get_display_name(self):
        return self._device_manager_obj.get_device_name()


# class SolarisBlockDeviceMixin(object):
#     @cached_method
#     def get_block_access_path(self):
#         return self.device.get_device_path()

#     @cached_method
#     def get_size_in_bytes(self):
#         return self.device.get_size_in_bytes()

# class SolarisSCSIDevice(SolarisSCSIDeviceMixin, SCSIDevice):
#     def __init__(self, device):
#         super(SolarisSCSIDevice, self).__init__()
#         self.device = device

#     @cached_method
#     def get_display_name(self):
#         return self.device.get_device_name()


class SolarisSCSIBlockDevice(SolarisSCSIDeviceMixin, SCSIBlockDevice):
    def __init__(self, device_manager_obj):
        super(SolarisSCSIBlockDevice, self).__init__()
        self._device_manager_obj = device_manager_obj

    @cached_method
    def get_block_access_path(self):
        return self.get_scsi_access_path()


class SolarisSCSIStorageControllerDevice(SolarisSCSIDeviceMixin, SCSIStorageController):
    def __init__(self, device_manager_obj):
        self._device_manager_obj = device_manager_obj


class SolarisSCSIModel(SCSIModel):
    def __init__(self, device_manager):
        self._device_manager = device_manager

    @cached_method
    def get_all_scsi_block_devices(self):
        return [SolarisSCSIBlockDevice(device) for device in self._device_manager.get_all_block_devices()]

    @cached_method
    def get_all_storage_controller_devices(self):
        return [SolarisSCSIStorageControllerDevice(device) for device in self._device_manager.get_all_scsi_storage_controllers()]