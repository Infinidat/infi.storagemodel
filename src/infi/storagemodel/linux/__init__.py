import os
import atexit

from ..base import StorageModel
from infi.pyutils.lazy import cached_method, cached_function
from datetime import datetime

from logging import getLogger, NullHandler
logger = getLogger(__name__)

def _get_all_host_bus_adapter_numbers():
    from infi.hbaapi import get_ports_collection
    return [port.hct[0] for port in get_ports_collection().get_ports()]

class LinuxStorageModel(StorageModel):
    def __init__(self):
        super(LinuxStorageModel, self).__init__()
        self.rescan_process = None
        self.rescan_process_start_time = None
        atexit.register(self.terminate_rescan_process, silent=True)

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

    def _create_disk_model(self):
        from .disk import LinuxDiskModel
        return LinuxDiskModel()

    def _create_mount_manager(self):
        from .mount import LinuxMountManager
        return LinuxMountManager()

    def _create_mount_repository(self):
        from .mount import LinuxMountRepository
        return LinuxMountRepository()

    def terminate_rescan_process(self, silent=False):
        try:
            from gipc.gipc import _GProcess as Process
        except ImportError:
            from multiprocessing import Process
        if isinstance(self.rescan_process, Process) and self.rescan_process.is_alive():
            if not silent:
                logger.debug("terminating previous rescan process")
            else:
                getLogger("gipc").addHandler(NullHandler())
            try:
                self.rescan_process.terminate()
            except Exception:
                if not silent:
                    logger.exception("Failed to terminate rescan process")
            self.rescan_process = None

    def initiate_rescan(self, wait_for_completion=True):
        from .rescan_scsi_bus import main
        try:
            from gipc.gipc import _GProcess as Process
            from gipc.gipc import start_process
        except ImportError:
            from multiprocessing import Process

            def start_process(*args, **kwargs):
                process = Process(*args, **kwargs)
                process.start()
                return process

        if isinstance(self.rescan_process, Process) and self.rescan_process.is_alive():
            if (datetime.now() - self.rescan_process_start_time).total_seconds() > 30:
                self.terminate_rescan_process()
                self.rescan_process = None
                self.initiate_rescan(wait_for_completion)
            else:
                logger.debug("previous rescan process is still running")
                return
        else:
            self.rescan_process_start_time = datetime.now()
            self.rescan_process = start_process(target=main, args=(_get_all_host_bus_adapter_numbers(),))
            logger.debug("rescan process started")
            if wait_for_completion:
                logger.debug("waiting for rescan process completion")
                self.rescan_process.join()
