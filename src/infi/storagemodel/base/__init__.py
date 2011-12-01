
from infi.pyutils.lazy import cached_method, clear_cache, LazyImmutableDict

class StorageModel(object):
    """StorageModel provides layered view of the storage stack.
    The layers currently offered by the model are the SCSI layer and the Multipath layer.
    
    All layers are fetched in a lazy and cached manner:
    
    - No information is gathers upon initialization
    
    - Information is gathered when it is asked for, and stored in a cache within the object
    
    - Every second request is pulled from the cache
    
    When you think tha the cache no longer up-to-date, you can clear it using the refresh() method
    """

    from .. import predicates

    def __init__(self):
        super(StorageModel, self).__init__()

    @cached_method
    def get_scsi(self):
        """:returns: a :class:`.SCSIModel` object which represents the :ref:`scsi-layer`"""
        return self._create_scsi_model()

    @cached_method
    def get_native_multipath(self):
        """:returns: an :class:`.MultipathFrameworkModel` object, as viewed by the OS built-in MPIO driver"""
        # TODO what to do in case native multipath is not installed?
        return self._create_native_multipath_model()

    @cached_method
    def get_disk(self):
        """:returns: an :class:`.DiskModel` object"""
        return self._create_disk_model()

    @cached_method
    def get_mount_manager(self):
        """:returns: an instance of Mount Manager"""
        return self._create_mount_manager()

    @cached_method
    def get_mount_repository(self):
        """:returns: an instance of Mount Manager"""
        return self._create_mount_repository()

    def refresh(self):
        """clears the model cache"""
        from ..connectivity import ConnectivityFactory
        clear_cache(self)
        clear_cache(ConnectivityFactory)

    def rescan_and_wait_for(self, predicate=None, timeout_in_seconds=60):
        """Rescan devices and polls the prediate until either it returns True or a timeout is reached.
        
        The model is refreshed automatically, there is no need to refresh() after calling this method or in the
        implementation of the predicate.
        
        For more information and usage examples, see :doc:`rescan`

        :param predicate: a callable object that returns either True or False. 
        
        :param timeout_in_seconds: time in seconds to poll the predicate.
        
        :raises: :exc:`infi.storagemodel.errors.TimeoutError` exception.
        """
        from time import time, sleep
        from sys import maxint
        from ..errors import TimeoutError
        if timeout_in_seconds is None:
            timeout_in_seconds = maxint
        if predicate is None:
            from ..predicates import WaitForNothing
            predicate = WaitForNothing()
        self.initiate_rescan()
        self.refresh()
        start_time = time()
        while not predicate():
            if time() - start_time >= timeout_in_seconds:
                raise TimeoutError() # pylint: disable=W0710
            sleep(1)
            self.initiate_rescan()
            self.refresh()

    #############################
    # Platform Specific Methods #
    #############################

    def initiate_rescan(self): # pragma: no cover
        """A premitive rescan method, if you do not wish to use the waiting mechanism"""
        # platform implementation
        raise NotImplementedError()

    def _create_scsi_model(self): # pragma: no cover
        # platform implementation
        raise NotImplementedError()

    def _create_native_multipath_model(self): # pragma: no cover
        # platform implementation
        raise NotImplementedError()

    def _create_disk_model(self): # pragma: no cover
        # platform implementation
        raise NotImplementedError()

    def _create_mount_manager(self): # pragma: no cover
        # platform implementation
        raise NotImplementedError()

    def _create_mount_repository(self): # pragma: no cover
        # platform implementation
        raise NotImplementedError()
