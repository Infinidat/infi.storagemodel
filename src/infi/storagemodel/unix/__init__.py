from infi.storagemodel.base import StorageModel
from infi.storagemodel.errors import RescanError
from datetime import datetime
import atexit

from logging import getLogger
logger = getLogger(__name__)

# pylint: disable=W0212,E1002

class UnixStorageModel(StorageModel):
    rescan_subprocess_timeout = 30

    def __init__(self):
        super(UnixStorageModel, self).__init__()
        self.rescan_process = None
        self.rescan_process_start_time = None
        self.server_and_worker = (None, None)
        atexit.register(self.terminate_rescan_process, silent=True)

    def _create_scsi_model(self):
        raise NotImplementedError()

    def _create_native_multipath_model(self):
        raise NotImplementedError()

    def _create_disk_model(self):
        raise NotImplementedError()

    def _create_mount_repository(self):
        raise NotImplementedError()

    def _create_utils(self):
        from infi.storagemodel.unix.utils import UnixUtils
        return UnixUtils()

    def rescan_method(self):
        # platform specific
        raise NotImplementedError()

    def block_on_rescan_process(self, event):
        from infi.storagemodel.base import gevent_wrapper
        try:
            with gevent_wrapper.blocking_context(None) as server_and_worker:
                model_without_cache = self.__class__()
                call_method, call_args = server_and_worker[1].prepare(model_without_cache.rescan_method)
                self.server_and_worker = server_and_worker
                return server_and_worker[1].call(call_method, call_args, timeout=self.rescan_subprocess_timeout)
        except:
            logger.exception('rescan method raised exception')
        finally:
            event.set()

    def join_on_rescan_process(self):
        logger.debug("waiting for rescan process completion")
        rescan_process = getattr(self, 'rescan_process')
        if rescan_process:
            rescan_process.join()
        self.terminate_rescan_process()

    def _initiate_rescan(self, wait_for_completion=True, raise_error=False):
        from infi.storagemodel.base import gevent_wrapper

        if self.rescan_process_start_time:
            if (datetime.now() - self.rescan_process_start_time).total_seconds() > self.rescan_subprocess_timeout:
                logger.debug("rescan process timed out, killing it")
                self.terminate_rescan_process()
                return self._initiate_rescan(wait_for_completion, raise_error)
            else:
                logger.debug("previous rescan process is still running")
                if wait_for_completion:
                    self.join_on_rescan_process()
        else:
            self.terminate_rescan_process()
            event = gevent_wrapper.Event()
            rescan_process = gevent_wrapper.spawn(self.block_on_rescan_process, event)
            event.wait()
            self.rescan_process = rescan_process
            logger.debug("rescan process started")
            if wait_for_completion:
                self.join_on_rescan_process()

    def terminate_rescan_process(self, silent=False):
        server_and_worker = getattr(self, 'server_and_worker', None)
        if server_and_worker[1]:
            logger.debug("terminating rescan process worker")
            server_and_worker[1].ensure_stopped()
        rescan_process = getattr(self, 'rescan_process', None)
        if rescan_process:
            logger.debug("waiting for rescan process to join, this should not block as it supposed to exit by now")
            rescan_process.join()
        self.server_and_worker = (None, None)
        self.rescan_process = None
