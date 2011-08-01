
from ..utils import cached_property, cached_method, clear_cache, LazyImmutableDict
from contextlib import contextmanager
from infi.exceptools import InfiException

from .inquiry import SupportedVPDPagesDict, InquiryInformationMixin
from .scsi import SCSIDevice, SCSIBlockDevice, SCSIModel, SCSIStorageController
from .multipath import MultipathDevice, Path, MultipathFrameworkModel, NativeMultipathModel
from .multipath import LoadBalancePolicy
from .multipath import FailoverOnly, RoundRobin, RoundRobinWithExplicitSubset, RoundRobinWithTPGSSubset
from .multipath import WeightedPaths, LeastBlocks, LeastQueueDepth

class TimeoutError(InfiException):
    pass

class StorageModel(object):
    def __init__(self):
        super(StorageModel, self).__init__()

    @cached_property
    def scsi(self):
        return self._create_scsi_model()

    @cached_property
    def native_multipath(self):
        return self._create_native_multipath_model()

    def refresh(self):
        from ..connectivity import ConnectivityFactory
        clear_cache(self)
        clear_cache(ConnectivityFactory)

    def rescan_and_wait_for(self, predicate, timeout_in_seconds=None):
        """Rescan devices and wait for user-defined predicate."""
        from time import time, sleep
        from sys import maxint
        if timeout_in_seconds is None:
            timeout_in_seconds = maxint
        self.initiate_rescan()
        self.refresh()
        start_time = time()
        while not predicate():
            if time() - start_time >= timeout_in_seconds:
                raise TimeoutError()
            sleep(1)
            self.refresh()

    #############################
    # Platform Specific Methods #
    #############################

    def initiate_rescan(self):
        # platform implementation
        raise NotImplementedError

    def _create_scsi_model(self):
        # platform implementation        
        raise NotImplementedError()

    def _create_native_multipath(self):
        # platform implementation
        raise NotImplementedError()

# TODO implement common rescan predicates
