
from infi.pyutils.lazy import cached_method
from contextlib import contextmanager

from .inquiry import InquiryInformationMixin

class MultipathFrameworkModel(object):
    def filter_non_multipath_scsi_block_devices(self, scsi_block_devices):
        """:returns: items from the list that are not part of multipath devices claimed by this framework"""
        hctl_list = [path.get_hctl() for path in [multipath.get_paths()  \
                                                  for multipath in self.get_all_multipath_devices()]]
        filter (lambda device: device.get_hctl() in hctl_list, scsi_block_devices)

    def filter_vendor_specific_devices(self, devices, vid_pid_tuple):
        """:returns: only the items from the devices list that are of the specific type"""
        return filter(lambda device: device.get_scsi_vid_pid() == vid_pid_tuple, devices)

    #############################
    # Platform Specific Methods #
    #############################

    @cached_method
    def get_all_multipath_devices(self):
        """:returns: all multipath devices claimed by this framework"""
        # platform implementation
        raise NotImplementedError # pragma: no cover

class NativeMultipathModel(MultipathFrameworkModel):
    pass

class MultipathDevice(InquiryInformationMixin, object):
    @cached_method
    def get_vendor(self):
        """:returns: a get_vendor-specific implementation from the factory based on the device's SCSI vid and pid"""
        from ..vendor  import VendorFactory
        return VendorFactory.create_multipath_by_vid_pid(self.get_scsi_vid_pid(), self)

    #############################
    # Platform Specific Methods #
    #############################

    @contextmanager
    def asi_context(self):
        # platform implementation
        raise NotImplementedError # pragma: no cover

    @cached_method
    def get_device_access_path(self):
        # platform implementation
        raise NotImplementedError # pragma: no cover

    @cached_method
    def get_display_name(self):
        # platform implementation
        raise NotImplementedError # pragma: no cover

    @cached_method
    def get_size_in_bytes(self):
        # platform implementation
        raise NotImplementedError # pragma: no cover

    @cached_method
    def get_paths(self):
        """:rtype: list of :class:`.Path` instances"""
        # platform implementation
        raise NotImplementedError # pragma: no cover

    @cached_method
    def get_policy(self):
        """:rtype: an instance of :class:`.LoadBalancePolicy`"""
        # platform implementation
        raise NotImplementedError # pragma: no cover

class LoadBalancePolicy(object):
    name = None
    def __init__(self):
        self._cache = dict()

    @cached_method
    def get_display_name(self):
        return self.name

    def apply_on_device(self, device):
        raise NotImplementedError # pragma: no cover

class FailoverOnly(LoadBalancePolicy):
    name = "Fail Over Only"

    def __init__(self, active_path_id):
        super(FailoverOnly, self).__init__()
        self.active_path_id = active_path_id

class RoundRobin(LoadBalancePolicy):
    name = "Round Robin"

class RoundRobinWithSubset(LoadBalancePolicy):
    name = "Round Robin with subset"

    def __init__(self, active_path_ids):
        super(RoundRobinWithSubset, self).__init__()
        self.active_path_ids = active_path_ids

class RoundRobinWithTPGSSubset(RoundRobinWithSubset):
    pass

class RoundRobinWithExplicitSubset(RoundRobinWithSubset):
    pass

class WeightedPaths(LoadBalancePolicy):
    """weights is dictionary mapping between Path IDs to their intger weight"""

    name = "Weighted Paths"
    def __init__(self, weights):
        super(WeightedPaths, self).__init__()
        # weights is a dict of (path_id, weight) items
        self.weights = weights

class LeastBlocks(LoadBalancePolicy):
    name = "Least Blocks"

class LeastQueueDepth(LoadBalancePolicy):
    name = "Least Queue Depth"

class Path(object):
    @cached_method
    def get_connectivity(self):
        """returns either an FCConnnectivity object or ISCSIConnectivity object"""
        from ..connectivity import ConnectivityFactory
        return ConnectivityFactory.get_by_device_with_hctl(self)

    @cached_method
    def get_display_name(self):
        return self.get_path_id()

    #############################
    # Platform Specific Methods #
    #############################

    @cached_method
    def get_path_id(self):
        """:returns: depending on the operating system:
        
                    - sdX on linux
                    - PathId on Windows"""
        # platform implementation
        raise NotImplementedError # pragma: no cover

    @cached_method
    def get_hctl(self):
        """:returns: a :class:`infi.dtypes.hctl.HCTL` object"""
        # platform implementation
        raise NotImplementedError # pragma: no cover

    @cached_method
    def get_state(self):
        """:returns: either "up" or "down"."""
        # platform implementation
        raise NotImplementedError # pragma: no cover
