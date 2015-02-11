import atexit

from ..base import StorageModel
from ..base.gevent_wrapper import sleep
from infi.pyutils.lazy import cached_method
from datetime import datetime

from logging import getLogger, NullHandler
logger = getLogger(__name__)


class LinuxStorageModel(StorageModel):
    rescan_subprocess_timeout = 30

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

    def _create_utils(self):
        from .utils import LinuxUtils
        return LinuxUtils()

    def terminate_rescan_process(self, silent=False):
        from ..base.gevent_wrapper import get_process_class
        Process = get_process_class()
        sleep(0)  # give time for gipc time to join on the defunct rescan process
        if isinstance(self.rescan_process, Process) and self.rescan_process.is_alive():
            if not silent:
                logger.debug("terminating previous rescan process")
            else:
                getLogger("gipc").addHandler(NullHandler())
            try:
                self.rescan_process.terminate()
                sleep(0)  # give time for gipc time to join on the defunct rescan process
            except Exception:
                if not silent:
                    logger.exception("Failed to terminate rescan process")
            self.rescan_process = None

    def initiate_rescan(self, wait_for_completion=True, raise_error=False):
        from .rescan_scsi_bus import main
        from ..base.gevent_wrapper import get_process_class, start_process
        Process = get_process_class()
        sleep(0)  # give time for gipc time to join on the defunct rescan process
        if isinstance(self.rescan_process, Process) and self.rescan_process.is_alive():
            if (datetime.now() - self.rescan_process_start_time).total_seconds() > self.rescan_subprocess_timeout:
                logger.debug("rescan process timed out, killing it")
                self.terminate_rescan_process()
                self.rescan_process = None
                self.initiate_rescan(wait_for_completion)
            else:
                logger.debug("previous rescan process is still running")
                if wait_for_completion:
                    logger.debug("waiting for rescan process completion")
                    if raise_error:
                        self.rescan_process.get()       # this joins + raises exceptions if there were any
                    else:
                        self.rescan_process.join()
        else:
            if isinstance(self.rescan_process, Process):
                logger.debug("previous rescan process exit code: {}".format(self.rescan_process.exitcode))
            self.rescan_process_start_time = datetime.now()
            self.rescan_process = start_process(main)
            logger.debug("rescan process started")
            if wait_for_completion:
                logger.debug("waiting for rescan process completion")
                if raise_error:
                    self.rescan_process.get()       # this joins + raises exceptions if there were any
                else:
                    self.rescan_process.join()
