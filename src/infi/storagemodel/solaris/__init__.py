from ..unix import UnixStorageModel
from native_multipath import SolarisNativeMultipathModel

# pylint: disable=W0212,E1002

class SolarisStorageModel(UnixStorageModel):
    def _create_scsi_model(self):
        raise NotImplementedError()

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
