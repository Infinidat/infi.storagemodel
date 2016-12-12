from infi.storagemodel.base import StorageModel
from infi.pyutils.lazy import cached_method


# pylint: disable=W0212,E1002

class WindowsStorageModel(StorageModel):
    def _create_scsi_model(self):
        from .scsi import WindowsSCSIModel
        return WindowsSCSIModel()

    def _create_native_multipath_model(self):
        from .native_multipath import WindowsNativeMultipathModel
        return WindowsNativeMultipathModel()

    def _create_veritas_multipath_model(self):
        return self._create_native_multipath_model()

    def _create_disk_model(self):
        from .disk import WindowsDiskModel
        return WindowsDiskModel()

    @cached_method
    def _create_mount_manager(self):
        from .mount import WindowsMountManager
        return WindowsMountManager()

    def _create_mount_repository(self):
        from .mount import WindowsMountRepository
        return WindowsMountRepository()

    def _create_utils(self):
        from .utils import WindowsUtils
        return WindowsUtils()

    def _initiate_rescan(self, wait_for_completion=True, raise_error=False):
        from infi.devicemanager import DeviceManager
        from infi.storagemodel.base.gevent_wrapper import joinall, defer, spawn
        dm = DeviceManager()
        rescan_callables = (defer(controller.rescan) for controller in dm.storage_controllers)
        greenlets = [spawn(item) for item in rescan_callables]
        if wait_for_completion:
            joinall(greenlets, raise_error=True)
