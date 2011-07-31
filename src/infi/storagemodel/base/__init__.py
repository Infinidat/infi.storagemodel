
from ..utils import cached_property, cached_method, clear_cache, LazyImmutableDict
from contextlib import contextmanager

from .inquiry import SupportedVPDPagesDict, InquiryInformationMixin
from .scsi import SCSIDevice, SCSIBlockDevice, SCSIModel, SCSIStorageController
from .multipath import MultipathDevice, Path, MultipathFrameworkModel, NativeMultipathModel
from .multipath import LoadBalancePolicy, LoadBalancingContext
from .multipath import FailoverOnly, RoundRobin, RoundRobinWithExplicitSubset, RoundRobinWithTPGSSubset
from .multipath import WeightedPaths, LeastBlocks, LeastQueueDepth

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

    def _create_scsi_model(self):
        # platform implementation        
        raise NotImplementedError()

    def _create_native_multipath(self):
        # platform implementation
        raise NotImplementedError()
