from ..unix import UnixStorageModel
from infi.execute import execute, execute_assert_success
from infi.execute.exceptions import ExecutionError
from infi.pyutils.lazy import cached_method

# pylint: disable=W0212,E1002

class SolarisStorageModel(UnixStorageModel):
    @cached_method
    def _get_device_manager(self):
        from .devicemanager import DeviceManager
        return DeviceManager()

    def _create_scsi_model(self):
        from .scsi import SolarisSCSIModel
        return SolarisSCSIModel(self._get_device_manager())

    def _create_native_multipath_model(self):
        from .native_multipath import SolarisNativeMultipathModel
        return SolarisNativeMultipathModel()

    def _create_veritas_multipath_model(self):
        from .veritas_multipath import SolarisVeritasMultipathModel
        return SolarisVeritasMultipathModel(self.get_scsi())

    def _create_disk_model(self):
        raise NotImplementedError()

    def _create_mount_manager(self):
        from .mount import SolarisMountManager
        return SolarisMountManager()

    def _create_mount_repository(self):
        from .mount import SolarisMountRepository
        return SolarisMountRepository()

    def rescan_method(self):
        res = execute("cfgadm -lao show_SCSI_LUN".split())
        if res.get_returncode() not in (0, 2):
            raise ExecutionError(res)
        execute_assert_success("devfsadm -vC".split())
        return 0
