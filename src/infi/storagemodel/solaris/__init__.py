from infi.storagemodel.base import StorageModel

# pylint: disable=W0212,E1002

class SolarisStorageModel(StorageModel):
    def _create_scsi_model(self):
        raise NotImplementedError()

    def _create_native_multipath_model(self):
        raise NotImplementedError()

    def _create_disk_model(self):
        raise NotImplementedError()

    def _create_mount_manager(self):
        raise NotImplementedError()

    def _create_mount_repository(self):
        raise NotImplementedError()

    def _create_utils(self):
        raise NotImplementedError()

    def initiate_rescan(self, wait_for_completion=False):
        raise NotImplementedError()
