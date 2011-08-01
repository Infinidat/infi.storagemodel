
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
        """Rescan devices and wait for user-defined predicate.
        There is no need to refresh() after calling this method."""
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

class LunInventoryChanged(object):
    def __init__(self):
        self.baseline = self._get_snapshot()

    def _get_snapshot(self):
        from .. import get_storage_model
        model = get_storage_model()
        disks = model.scsi.get_all_scsi_block_devices()
        hctl_mappings = {}
        for disk in disks:
            hctl_mappings[disk.hctl] = disk.scsi_serial_number
        return hctl_mappings

    def __call__(self):
        current = self._get_snapshot()
        # find new disks
        for disk in current:
            if disk.hctl not in self.baseline.keys():
                return True
        # find removed disks
        for disk in self.baseline:
            if disk.hctl not in current.keys():
                return True
        return False


class PredicateList(object):
    def __init__(self, list_of_predicates):
        self._list_of_predicates = list_of_predicates

    def __call__(self):
        for predicate in self._list_of_predicates:
            if predicate():
                return True
        return False

class DiskArrived(object):
    def __init__(self, scsi_serial_number):
        pass

class DiskWentAway(object):
    def __init__(self, scsi_serial_number):
        pass

class NewLunMapping(object):
    def by_iscsi(self):
        raise NotImplementedError

    def by_fc(self, initiator_wwn, target_wwn, lun_number):
        pass

class LunWentAway(object):
    def by_iscsi(self):
        raise NotImplementedError

    def by_fc(self, initiator_wwn, target_wwn, lun_number):
        pass
