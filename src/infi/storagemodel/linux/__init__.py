from ..unix import UnixStorageModel
from infi.pyutils.lazy import cached_method


class LinuxStorageModel(UnixStorageModel):
    @cached_method
    def _get_sysfs(self):
        from .sysfs import Sysfs
        return Sysfs()

    def _create_scsi_model(self):
        from .scsi import LinuxSCSIModel
        return LinuxSCSIModel(self._get_sysfs())

    def _create_native_multipath_model(self):
        from .native_multipath import LinuxNativeMultipathModel
        return LinuxNativeMultipathModel(self._get_sysfs())

    def _create_veritas_multipath_model(self):
        from .veritas_multipath import LinuxVeritasMultipathModel
        return LinuxVeritasMultipathModel(self._get_sysfs(), self.get_scsi())

    def _create_disk_model(self):
        from .disk import LinuxDiskModel
        return LinuxDiskModel()

    def _create_mount_manager(self):
        from .mount import LinuxMountManager
        return LinuxMountManager()

    def _create_mount_repository(self):
        from .mount import LinuxMountRepository
        return LinuxMountRepository()

    def rescan_method(self):
        from .rescan_scsi_bus import main
        from .iscsi import iscsi_rescan
        iscsi_rescan()
        return main(timeout=max(self.rescan_subprocess_timeout-10, 10))
