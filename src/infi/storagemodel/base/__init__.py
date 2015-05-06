from .gevent_wrapper import sleep
from infi.pyutils.lazy import cached_method, clear_cache
from logging import getLogger

logger = getLogger(__name__)


class StorageModel(object):
    """StorageModel provides a layered view of the storage stack.
    The layers currently exposed by the model are:

    * SCSI
    * Multipath
    * Disks
    * Mounts
    * Utils

    All layers are fetched lazily and cached inside the model. When you think that the cache no longer up-to-date,
    you can clear it using the refresh() method
    """

    # This import is for making it easier to work with storagemodel over rpyc
    from .. import predicates

    def __init__(self):
        super(StorageModel, self).__init__()

    @cached_method
    def get_scsi(self):
        """Returns a `infi.storagemodel.base.scsi.SCSIModel` object which represents the SCSI layer"""
        return self._create_scsi_model()

    @cached_method
    def get_native_multipath(self):
        """Returns a `infi.storagemodel.base.multipath.MultipathFrameworkModel` object, as seen by the operating system's built-in MPIO driver"""
        # TODO what to do in case native multipath is not installed?
        return self._create_native_multipath_model()

    @cached_method
    def get_veritas_multipath(self):
        """Returns a `infi.storagemodel.base.multipath.MultipathFrameworkModel` object, as seen by the operating system's built-in MPIO driver"""
        # TODO what to do in case native multipath is not installed?
        return self._create_veritas_multipath_model()

    @cached_method
    def get_disk(self):
        """Returns a `infi.storagemodel.base.disk.DiskModel` object which represents the disks layer"""
        return self._create_disk_model()

    @cached_method
    def get_mount_manager(self):
        """Returns an instance of `infi.storagemodel.base.mount.MountManager` """
        return self._create_mount_manager()

    @cached_method
    def get_mount_repository(self):
        """Returns an instance of `infi.storagemodel.base.mount.MountRepository` """
        return self._create_mount_repository()

    @cached_method
    def get_utils(self):
        """Returns an instance of `infi.storagemodel.base.utils.Utils` """
        return self._create_utils()

    def refresh(self):
        """clears the model cache"""
        from ..connectivity import ConnectivityFactory
        clear_cache(self)
        clear_cache(ConnectivityFactory)

    def _try_predicate(self, predicate):
        """Returns True/False if the predicate returned, None on RescanIsNeeded exception"""
        from infi.storagemodel.errors import RescanIsNeeded, TimeoutError, StorageModelError
        try:
            return predicate()
        except (RescanIsNeeded, TimeoutError, StorageModelError) as error:
            logger.debug("Predicate {!r} raised {!r} during rescan".format(predicate, error), exc_info=True)
            return None
        except:
            logger.exception("An un-expected exception was raised by predicate {!r}".format(predicate))
            raise

    def rescan_and_wait_for(self, predicate=None, timeout_in_seconds=60, **rescan_kwargs):
        """Rescan devices and poll the predicate until either it returns True or a timeout is reached.

        The model is refreshed automatically, there is no need to `refresh` after calling this method or in the
        implementation of the predicate.

        **predicate**: a callable object that returns either True or False.

        **timeout_in_seconds**: time in seconds to poll the predicate.

        **rescan_kwargs**: additional keyword arguments to pass to `_initiate_rescan`.

        Raises `infi.storagemodel.errors.TimeoutError` exception if the timeout is reached.
        """
        from time import time
        from sys import maxsize
        from ..errors import TimeoutError
        if timeout_in_seconds is None:
            timeout_in_seconds = maxsize
        if predicate is None:
            from ..predicates import WaitForNothing
            predicate = WaitForNothing()
        self.refresh()
        start_time = time()
        logger.debug("Initiating rescan with keyword arguments {!r}".format(rescan_kwargs))
        self._initiate_rescan(**rescan_kwargs)
        while True:
            logger.debug("Trying predicate: {!r}".format(predicate))
            result = self._try_predicate(predicate)
            if result is True:
                logger.debug("Predicate returned True, finished rescanning")
                break
            elif time() - start_time >= timeout_in_seconds:
                logger.debug("Rescan did not complete before timeout")
                raise TimeoutError()  # pylint: disable=W0710
            elif result in [False, None]:
                logger.debug("Predicate returned False, will rescan again")
                self.retry_rescan(**rescan_kwargs)
            sleep(1)
            self.refresh()

    def retry_rescan(self, **rescan_kwargs):
        self._initiate_rescan(**rescan_kwargs)


    #############################
    # Platform Specific Methods #
    #############################

    def _initiate_rescan(self, wait_for_completion=False, raise_error=False):  # pragma: no cover
        """A primitive rescan method that can be used in case you do not need the more elaborate rescan_and_wait_for method. """
        # platform implementation
        raise NotImplementedError()

    def _create_scsi_model(self):  # pragma: no cover
        # platform implementation
        raise NotImplementedError()

    def _create_native_multipath_model(self):  # pragma: no cover
        # platform implementation
        raise NotImplementedError()

    def _create_veritas_multipath_model(self):  # pragma: no cover
        # Naive implementation is empty
        from infi.storagemodel.base.multipath import VeritasMultipathModel
        return VeritasMultipathModel()

    def _create_disk_model(self):  # pragma: no cover
        # platform implementation
        raise NotImplementedError()

    def _create_mount_manager(self):  # pragma: no cover
        # platform implementation
        raise NotImplementedError()

    def _create_mount_repository(self):  # pragma: no cover
        # platform implementation
        raise NotImplementedError()

    def _create_utils(self):  # pragma: no cover
        # platform implementation
        raise NotImplementedError()
