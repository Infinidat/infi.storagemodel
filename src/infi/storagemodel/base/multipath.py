from itertools import chain
from infi.pyutils.lazy import cached_method
from contextlib import contextmanager

from .inquiry import InquiryInformationMixin

class MultipathFrameworkModel(object):
    def filter_non_multipath_scsi_block_devices(self, scsi_block_devices):
        """:returns: items from the list that are not part of multipath devices claimed by this framework"""
        hctl_list = [path.get_hctl() for path in chain.from_iterable(multipath.get_paths()  \
                                                                     for multipath in self.get_all_multipath_devices())]
        return filter(lambda device: device.get_hctl() in hctl_list, scsi_block_devices)

    def filter_vendor_specific_devices(self, devices, vid_pid_tuple):
        """:returns: only the items from the devices list that are of the specific type"""
        return filter(lambda device: device.get_scsi_vid_pid() == vid_pid_tuple, devices)

    def find_multipath_device_by_block_access_path(self, path):
        """:returns: :class:`MultipathDevice` object that matches the given path. 
        :raises: KeyError if no such device is found"""
        devices_dict = dict([(device.get_block_access_path(), device) for device in self.get_all_multipath_devices()])
        return devices_dict[path]

    #############################
    # Platform Specific Methods #
    #############################

    @cached_method
    def get_all_multipath_devices(self): # pragma: no cover
        """:returns: all multipath devices claimed by this framework"""
        # platform implementation
        raise NotImplementedError()

class NativeMultipathModel(MultipathFrameworkModel):
    pass

class MultipathDevice(InquiryInformationMixin, object):
    @cached_method
    def get_vendor(self):
        """:returns: a get_vendor-specific implementation from the factory based on the device's SCSI vid and pid"""
        from ..vendor  import VendorFactory
        return VendorFactory.create_multipath_by_vid_pid(self.get_scsi_vid_pid(), self)

    @cached_method
    def get_disk_drive(self): # pragma: no cover
        """:returns: a :class:`.DiskDevice` object
        :raises: NoSuchDisk"""
        from infi.storagemodel import get_storage_model
        model = get_storage_model().get_disk()
        return model.find_disk_drive_by_block_access_path(self.get_block_access_path())

    #############################
    # Platform Specific Methods #
    #############################

    @contextmanager
    def asi_context(self): # pragma: no cover
        """:returns: an infi.asi context"""
        # platform implementation
        raise NotImplementedError()

    @cached_method
    def get_block_access_path(self): # pragma: no cover
        """:returns: a path for the device"""
        # platform implementation
        raise NotImplementedError()

    @cached_method
    def get_display_name(self): # pragma: no cover
        """:returns: a string represtation for the device"""
        # platform implementation
        raise NotImplementedError()

    @cached_method
    def get_size_in_bytes(self): # pragma: no cover
        """:returns: size in bytes"""
        # platform implementation
        raise NotImplementedError()

    @cached_method
    def get_paths(self): # pragma: no cover
        """:rtype: list of :class:`.Path` instances"""
        # platform implementation
        raise NotImplementedError()

    @cached_method
    def get_policy(self): # pragma: no cover
        """:rtype: an instance of :class:`.LoadBalancePolicy`"""
        # platform implementation
        raise NotImplementedError()

class LoadBalancePolicy(object):
    name = None
    def __init__(self):
        self._cache = dict()

    @cached_method
    def get_display_name(self):
        """:returns: display name"""
        return self.name

    def apply_on_device(self, device): # pragma: no cover
        raise NotImplementedError()

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
    def get_path_id(self): # pragma: no cover
        """:returns: depending on the operating system:
        
                    - sdX on linux
                    - PathId on Windows"""
        # platform implementation
        raise NotImplementedError()

    @cached_method
    def get_hctl(self): # pragma: no cover
        """:returns: a :class:`infi.dtypes.hctl.HCTL` object"""
        # platform implementation
        raise NotImplementedError()

    @cached_method
    def get_state(self): # pragma: no cover
        """:returns: either "up" or "down"."""
        # platform implementation
        raise NotImplementedError()
