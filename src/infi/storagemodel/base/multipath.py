
from ..utils import cached_property, cached_method
from contextlib import contextmanager

from .inquiry import InquiryInformationMixin

class MultipathFrameworkModel(object):
    def filter_non_multipath_scsi_block_devices(self, scsi_block_devices):
        """ returns items from the list that are not part of multipath devices claimed by this framework"""
        hctl_list = [path.hctl for path in [multipath.paths for multipath in self.get_all_multipath_devices()]]
        filter (lambda device: device.hctl in hctl_list, scsi_block_devices)

    def filter_vendor_specific_devices(self, devices, vid_pid_tuple):
        """returns only the items from the devices list that are of the specific type"""
        return filter(lambda x: x.scsi_vid_pid == vid_pid_tuple, devices)

    #############################
    # Platform Specific Methods #
    #############################

    @cached_method
    def get_all_multipath_devices(self):
        """ returns all multipath devices claimed by this framework"""
        # platform implementation
        raise NotImplementedError

class NativeMultipathModel(MultipathFrameworkModel):
    pass

class MultipathDevice(InquiryInformationMixin, object):
    @cached_property
    def vendor(self):
        """Returns a vendor-specific implementation from the factory based on the device's SCSI vid and pid"""
        from ..vendor import VendorFactory
        return VendorFactory.create_multipath_by_vid_pid(self.scsi_vid_pid, self)

    #############################
    # Platform Specific Methods #
    #############################

    @contextmanager
    def asi_context(self):
        # platform implementation
        raise NotImplementedError

    @cached_property
    def device_access_path(self):
        # platform implementation
        raise NotImplementedError

    @cached_property
    def display_name(self):
        # platform implementation
        raise NotImplementedError

    @cached_property
    def size_in_bytes(self):
        # platform implementation
        raise NotImplementedError

    @cached_property
    def paths(self):
        # platform implementation
        raise NotImplementedError

    @cached_property
    def policy(self):
        self._platform_specific_policy_context.get_policy_for_device(self)

    def set_new_policy(self, policy):
        # we're not going to do this now
        raise NotImplementedError

    @cached_property
    def _platform_specific_policy_context(self):
        raise NotImplementedError

class LoadBalancingContext(object):
    def get_policy_for_device(self, device):
        raise NotImplementedError

    def apply_policy_on_device(self, device, policy):
        policy.apply_on_device(device)

class LoadBalancePolicy(object):
    _name = None
    def __init__(self):
        self._cache = dict()

    @cached_property
    def display_name(self):
        return self._name

    def apply_on_device(self, device):
        raise NotImplementedError

class FailoverOnly(LoadBalancePolicy):
    _name = "FailOverOnly"

    def __init__(self, active_path_id):
        super(FailoverOnly, self).__init__()
        self._cache["active_path_id"] = active_path_id

    @cached_property
    def active_path_id(self):
        pass

class RoundRobin(LoadBalancePolicy):
    _name = "Round Robin"

class RoundRobinWithSubset(LoadBalancePolicy):
    _name = "Round Robin with subset"

    def __init__(self, active_path_ids):
        super(RoundRobinWithSubset, self).__init__()
        self._cache["active_path_ids"] = active_path_ids

    @property
    def active_path_ids(self):
        pass

class RoundRobinWithTPGSSubset(RoundRobinWithSubset):
    pass

class RoundRobinWithExplicitSubset(RoundRobinWithSubset):
    pass

class WeightedPaths(LoadBalancePolicy):
    _name = "Weighted Paths"
    def __init__(self, weights):
        super(WeightedPaths, self).__init__()
        self._cache['weights'] = weights

    @property
    def weights(self):
        pass

class LeastBlocks(LoadBalancePolicy):
    _name = "Least Blocks"

class LeastQueueDepth(LoadBalancePolicy):
    _name = "Least Queue Depth"

class Path(object):
    @cached_property
    def connectivity(self):
        """returns either an FCConnnectivity object or ISCSIConnectivity object"""
        from ..connectivity import ConnectivityFactory
        return ConnectivityFactory.get_by_device_with_hctl(self)

    #############################
    # Platform Specific Methods #
    #############################

    @cached_property
    def path_id(self):
        """sdX on linux, PathId on Windows"""
        # platform implementation
        raise NotImplementedError

    @cached_property
    def hctl(self):
        # platform implementation
        raise NotImplementedError

    @cached_property
    def state(self):
        """up/down"""
        # platform implementation
        raise NotImplementedError
