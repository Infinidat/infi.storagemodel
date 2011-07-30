
from ..utils import cached_property, cached_method
from contextlib import contextmanager

from .inquiry import InquiryInformationMixin

class MultipathFrameworkModel(object):
    def filter_non_multipath_scsi_block_devices(self, scsi_block_devices):
        """ returns items from the list that are not part of multipath devices claimed by this framework
        """
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
        """ returns all multipath devices claimed by this framework
        """
        # platform implementation
        raise NotImplementedError


class NativeMultipathModel(MultipathFrameworkModel):
    pass

class MultipathDevice(InquiryInformationMixin, object):
    @contextmanager
    def asi_context(self):
        # platform implementation
        raise NotImplementedError

    @cached_property
    def device_access_path(self):
        """ linux: /dev/dm-X
        windows: mpiodisk%d
        """
        # platform implementation
        raise NotImplementedError

    @cached_property
    def display_name(self):
        """ linux: mpathX
        windows: physicaldrive
        """
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
        """ 'failover only', 'round robin', 'weighted round robin', 'least queue depth', 'least blocks',
        'round robin with subset'
        not all policies are supported on all platforms
        """
        # return a Policy object (FailOverOnly/Custom/...)
        # platform implementation
        raise NotImplementedError

    @cached_property
    def policy_attributes(self):
        """ names of path attributes relevant to this policy
        """
        # platform implementation
        raise NotImplementedError

    def apply_policy(self, policy_builder):
        """
        linux: 
            failover only: group per path
            round-robin: all paths in one group, we ignore path states, weights
            weighted-paths: all paths in one group, allow weights
            round-robin with subset: not supported
            least queue depth: all paths in one group, selector is queue-length, not supported on all all distros
            least blocks: all paths in hour group, select is service-time, not supported on all distros
        windows: 
            round-robin with subset: not supported
            on invalid policy, ValueError is raised
            """
        # platform implementation
        raise NotImplementedError

    @cached_property
    def vendor(self):
        """ Returns a vendor-specific implementation from the factory based on the device's SCSI vid and pid"""
        from ..vendor import VendorFactory
        return VendorFactory.create_multipath_by_vid_pid(self.scsi_vid_pid, self)

class FailoverOnlyBuilder(object):
    pass

class RoundRobinWithSubsetBuilder(object):
    def use_tpgs(self):
        return self

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


# TODO the policy strategy
