from contextlib import contextmanager
from ..base import scsi, gevent_wrapper
from infi.pyutils.lazy import cached_method
from infi.storagemodel.base.scsi import SCSIBlockDevice, SCSIStorageController, SCSIModel

QUERY_TIMEOUT_IN_SECONDS = 3

class SolarisSCSIDeviceMixin(object):
    @contextmanager
    def asi_context(self):
        from infi.asi import create_platform_command_executer, create_os_file

        handle = create_os_file(self.get_scsi_access_path())
        executer = create_platform_command_executer(handle, timeout=QUERY_TIMEOUT_IN_SECONDS)
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

    def is_device_ready(self, dev):
        from infi.storagemodel.errors import DeviceError
        try:
            return dev.get_scsi_test_unit_ready()
        except DeviceError:
            return False

    @cached_method
    def get_all_scsi_block_devices(self):
        devs = [SolarisSCSIBlockDevice(device) for device in \
                self._device_manager.get_all_scsi_block_devices()]
        return [d for d in devs if self.is_device_ready(d)]

    @cached_method
    def get_all_storage_controller_devices(self):
        devs = [SolarisSCSIStorageControllerDevice(device) \
                for device in self._device_manager.get_all_scsi_storage_controllers()]
        return [d for d in devs if self.is_device_ready(d)]
