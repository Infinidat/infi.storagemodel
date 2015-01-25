from infi.storagemodel.base import StorageModel

# pylint: disable=W0212,E1002

class UnixStorageModel(StorageModel):
    def _create_scsi_model(self):
        raise NotImplementedError()

    def _create_native_multipath_model(self):
        raise NotImplementedError()

    def _create_disk_model(self):
        raise NotImplementedError()

    def _create_mount_repository(self):
        raise NotImplementedError()

    def _create_utils(self):
        from ..unix.utils import UnixUtils
        return UnixUtils()

    def initiate_rescan(self, wait_for_completion=False):
        raise NotImplementedError()
