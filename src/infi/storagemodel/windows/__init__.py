from ..base import StorageModel

# pylint: disable=W0212,E1002

class WindowsStorageModel(StorageModel):
    def _create_scsi_model(self):
        from .scsi import WindowsSCSIModel
        return WindowsSCSIModel()

    def _create_native_multipath_model(self):
        from .native_multipath import WindowsNativeMultipathModel
        return WindowsNativeMultipathModel()

    def _create_disk_model(self):
        from .disk import WindowsDiskModel
        return WindowsDiskModel()

    def _create_mount_manager(self):
        from .mount import WindowsMountManager
        return WindowsMountManager()

    def _create_mount_repository(self):
        from .mount import WindowsMountRepository
        return WindowsMountRepository()

    def initiate_rescan(self, wait_for_completion=False):
        from infi.devicemanager import DeviceManager
        dm = DeviceManager()
        for controller in dm.storage_controllers:
            if not controller.is_real_device():
                continue
            controller.rescan()
