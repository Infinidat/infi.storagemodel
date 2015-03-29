from infi.pyutils.lazy import cached_method
from ..unix import UnixStorageModel
from devicemanager import DeviceManager
from native_multipath import SolarisNativeMultipathModel

# pylint: disable=W0212,E1002

class SolarisStorageModel(UnixStorageModel):
    @cached_method
    def _get_device_manager(self):
        return DeviceManager()

    def _create_scsi_model(self):
        from .scsi import SolarisSCSIModel
        return SolarisSCSIModel(self._get_device_manager())

    def _create_native_multipath_model(self):
        return SolarisNativeMultipathModel()

    def _create_disk_model(self):
        raise NotImplementedError()

    def _create_mount_manager(self):
        from .mount import SolarisMountManager
        return SolarisMountManager()

    def _create_mount_repository(self):
        from .mount import SolarisMountRepository
        return SolarisMountRepository()

    def initiate_rescan(self, wait_for_completion=False):
        raise NotImplementedError()
