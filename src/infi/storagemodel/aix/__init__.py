from ..unix import UnixStorageModel


class AixStorageModel(UnixStorageModel):
    def _create_scsi_model(self):
        from .scsi import AixSCSIModel
        return AixSCSIModel()

    def _create_native_multipath_model(self):
        from .native_multipath import AixNativeMultipathModel
        return AixNativeMultipathModel()

    def _create_disk_model(self):
        raise NotImplementedError()

    def _create_mount_manager(self):
        raise NotImplementedError()

    def _create_mount_repository(self):
        raise NotImplementedError()

    def _create_veritas_multipath_model(self):
        raise NotImplementedError()

    def rescan_method(self):
        from .rescan import AixRescan
        AixRescan().rescan()
        return 0

    def refresh(self):
        from infi.pyutils.lazy import clear_cache
        from .scsi import AixSCSIDevice
        super(AixStorageModel, self).refresh()
        clear_cache(AixSCSIDevice)
