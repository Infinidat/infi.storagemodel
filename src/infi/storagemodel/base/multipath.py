from itertools import chain
from infi.pyutils.lazy import cached_method
from contextlib import contextmanager
from .inquiry import SCSICommandInformationMixin


class MultipathFrameworkModel(object):
    def filter_non_multipath_scsi_block_devices(self, scsi_block_devices):
        """Returns items from the list that are not part of multipath devices claimed by this framework"""
        hctl_list = [path.get_hctl() for path in chain.from_iterable(multipath.get_paths()
                                                                     for multipath in self.get_all_multipath_block_devices())]
        return [device for device in scsi_block_devices if device.get_hctl() not in hctl_list]

    def filter_non_multipath_scsi_storage_controller_devices(self, scsi_controller_devices):
        """Returns items from the list that are not part of multipath devices claimed by this framework"""
        hctl_list = [path.get_hctl() for path in chain.from_iterable(multipath.get_paths()
                                                                     for multipath in self.get_all_multipath_storage_controller_devices())]
        return [device for device in scsi_controller_devices if device.get_hctl() not in hctl_list]

    def filter_vendor_specific_devices(self, devices, vid_pid_tuple):
        """Returns only the items from the devices list that are of the specific type"""
        from infi.storagemodel.base.gevent_wrapper import run_together
        run_together(device.get_scsi_vendor_id_or_unknown_on_error for device in devices)
        return [device for device in devices if device.get_scsi_vendor_id_or_unknown_on_error() == vid_pid_tuple]

    def find_multipath_device_by_block_access_path(self, path):
        """
        Returns `infi.storagemodel.base.multipath.MultipathBlockDevice` object that matches the given path.

        Raises `KeyError` if no such device is found.
        """
        from infi.storagemodel.linux.native_multipath import LinuxNativeMultipathBlockDevice
        from infi.storagemodel.windows.native_multipath import WindowsNativeMultipathBlockDevice
        devices_dict = dict([(device.get_block_access_path(), device) for device in self.get_all_multipath_block_devices()])
        for value in devices_dict.values():
            if isinstance(value, LinuxNativeMultipathBlockDevice):
                devices_dict[value.get_device_mapper_access_path()] = value
            if isinstance(value, WindowsNativeMultipathBlockDevice):
                devices_dict[r"\\.\{}".format(value.get_display_name())] = value
        if path in devices_dict:
            return devices_dict[path]
        if path.upper() in devices_dict:
            return devices_dict[path.upper()]
        raise KeyError(path)

    #############################
    # Platform Specific Methods #
    #############################

    @cached_method
    def get_all_multipath_block_devices(self):  # pragma: no cover
        """Returns all multipath block devices claimed by this framework"""
        # platform implementation
        raise NotImplementedError()

    @cached_method
    def get_all_multipath_storage_controller_devices(self):  # pragma: no cover
        """Returns all multipath storage controller devices claimed by this framework"""
        # platform implementation
        raise NotImplementedError()

class NativeMultipathModel(MultipathFrameworkModel):
    # pylint: disable=W0223
    pass

class VeritasMultipathModel(MultipathFrameworkModel):
    @cached_method
    def get_all_multipath_block_devices(self):  # pragma: no cover
        return []

    @cached_method
    def get_all_multipath_storage_controller_devices(self):  # pragma: no cover
        return []

class MultipathDevice(object):
    pass

class MultipathStorageController(SCSICommandInformationMixin, MultipathDevice):
    @cached_method
    def get_vendor(self):
        """Returns a get_vendor-specific implementation from the factory based on the device's SCSI vid and pid"""
        from ..vendor import VendorFactory
        return VendorFactory.create_multipath_controller_by_vid_pid(self.get_scsi_vid_pid(), self)

    #############################
    # Platform Specific Methods #
    #############################

    @contextmanager
    def asi_context(self):  # pragma: no cover
        """Returns an `infi.asi` context"""
        # platform implementation
        raise NotImplementedError()

    @cached_method
    def get_multipath_access_path(self):  # pragma: no cover
        """Returns a path for the device"""
        # platform implementation
        raise NotImplementedError()

    @cached_method
    def get_display_name(self):  # pragma: no cover
        """Returns a string represtation for the device"""
        # platform implementation
        raise NotImplementedError()

    @cached_method
    def get_paths(self):  # pragma: no cover
        """Returns a list of `infi.storagemodel.base.multipath.Path` instances"""
        # platform implementation
        raise NotImplementedError()

    @cached_method
    def get_policy(self):  # pragma: no cover
        """Returns an instance of `infi.storagemodel.base.multipath.LoadBalancePolicy`"""
        # platform implementation
        raise NotImplementedError()

    def __repr__(self):
        return "<{} {} for {}>".format(self.__class__.__name__,
            self.get_multipath_access_path(), self.get_display_name())

class MultipathBlockDevice(SCSICommandInformationMixin, MultipathDevice):
    @cached_method
    def get_vendor(self):
        """Returns a get_vendor-specific implementation from the factory based on the device's SCSI vid and pid"""
        from ..vendor import VendorFactory
        return VendorFactory.create_multipath_block_by_vid_pid(self.get_scsi_vid_pid(), self)

    @cached_method
    def get_disk_drive(self):  # pragma: no cover
        """
        Returns a `infi.storagemodel.base.disk.DiskDrive` instance.

        Raises `infi.storagemodel.base.disk.NoSuchDisk` if not found.
        """
        from infi.storagemodel import get_storage_model
        model = get_storage_model().get_disk()
        return model.find_disk_drive_by_block_access_path(self.get_block_access_path())

    @cached_method
    def get_size_in_bytes(self):
        from infi.asi.coroutines.sync_adapter import sync_wait
        from infi.asi.cdb.read_capacity import ReadCapacity10Command, ReadCapacity16Command

        with self.asi_context() as asi:
            for command in [ReadCapacity16Command, ReadCapacity10Command]:
                try:
                    result = sync_wait(command().execute(asi))
                    return result.last_logical_block_address * result.block_length_in_bytes
                except:
                    pass
            return 0

    @cached_method
    def is_thin_provisioned(self):
        LOGICAL_BLOCK_PROVISIONING_VPD_PAGE = 0xb2
        PROV_TYPE_THIN = 2   # 0 = N/A, 1 = thick, 2 = thin
        vpd_page = self.get_scsi_inquiry_pages()[LOGICAL_BLOCK_PROVISIONING_VPD_PAGE]
        return vpd_page.provisioning_type == PROV_TYPE_THIN

    #############################
    # Platform Specific Methods #
    #############################

    @contextmanager
    def asi_context(self):  # pragma: no cover
        """Returns an infi.asi context"""
        # platform implementation
        raise NotImplementedError()

    @cached_method
    def get_block_access_path(self):  # pragma: no cover
        """Returns a path for the device"""
        # platform implementation
        raise NotImplementedError()

    @cached_method
    def get_display_name(self):  # pragma: no cover
        """Returns a string represtation for the device"""
        # platform implementation
        raise NotImplementedError()

    @cached_method
    def get_paths(self):  # pragma: no cover
        """Returns a list of `infi.storagemodel.base.multipath.Path` instances"""
        # platform implementation
        raise NotImplementedError()

    @cached_method
    def get_policy(self):  # pragma: no cover
        """Returns an instance of `infi.storagemodel.base.multipath.LoadBalancePolicy`"""
        # platform implementation
        raise NotImplementedError()

    def __repr__(self):
        return "<{} {} for {}>".format(self.__class__.__name__,
            self.get_block_access_path(), self.get_display_name())

class LoadBalancePolicy(object):
    """ Base class of all available load balancing policies """

    name = None
    def __init__(self):
        self._cache = dict()

    @cached_method
    def get_display_name(self):
        """Returns this policy's display name"""
        return self.name

class FailoverOnly(LoadBalancePolicy):
    """ Load balancing policy where the alternative paths are used only in case the active path fails. """
    # pylint: disable=W0223
    # The methods below are overriden by platform-specific implementations

    name = "Fail Over Only"

    def __init__(self, active_path_id):
        super(FailoverOnly, self).__init__()
        self.active_path_id = active_path_id

class RoundRobin(LoadBalancePolicy):
    """ Load balancing policy where all paths are used in a balanced way. """
    # pylint: disable=W0223
    # The methods below are overriden by platform-specific implementations
    name = "Round Robin"

class RoundRobinWithSubset(LoadBalancePolicy):
    """ Load balancing policy where a subset of the paths are used in a balanced way. """
    # pylint: disable=W0223
    # The methods below are overriden by platform-specific implementations
    name = "Round Robin with subset"

    def __init__(self, active_path_ids):
        """**active_path_ids**: a list of path ids that should be used"""
        super(RoundRobinWithSubset, self).__init__()
        self.active_path_ids = active_path_ids

class RoundRobinWithTPGSSubset(RoundRobinWithSubset):
    """ Load balancing policy where only paths that are active/optimized according to TPGS are used """
    # pylint: disable=W0223
    # The methods below are overriden by platform-specific implementations
    pass

class RoundRobinWithExplicitSubset(RoundRobinWithSubset):
    """ Load balancing policy where an explicitly-given subset of the paths are used """
    # pylint: disable=W0223
    # The methods below are overriden by platform-specific implementations
    pass

class WeightedPaths(LoadBalancePolicy):
    """ Load balancing policy that assigns a weight to each path. The weight indicates the relative priority of a
        given path. The larger the number, the lower ranked the priority. """
    # pylint: disable=W0223
    # The methods below are overriden by platform-specific implementations
    name = "Weighted Paths"
    def __init__(self, weights):
        """**weights**: a dictionary mapping from Path IDs to their integer weight"""
        super(WeightedPaths, self).__init__()
        # weights is a dict of (path_id, weight) items
        self.weights = weights

class LeastBlocks(LoadBalancePolicy):
    """ Load balancing policy that sends I/O down the path with the least number of data blocks currently being processed """
    # pylint: disable=W0223
    # The methods below are overriden by platform-specific implementations
    name = "Least Blocks"

class LeastQueueDepth(LoadBalancePolicy):
    """ Load balancing policy that sends I/O down the path with the fewest currently outstanding I/O requests. """
    # pylint: disable=W0223
    # The methods below are overriden by platform-specific implementations
    name = "Least Queue Depth"

class PathStatistics(object):
    def __init__(self, bytes_read, bytes_written, number_reads, number_writes):
        self._bytes_read = bytes_read
        self._bytes_written = bytes_written
        self._number_reads = number_reads
        self._number_writes = number_writes

    @property
    def bytes_read(self):
        return self._bytes_read
    @property
    def read_io_count(self):
        return self._number_reads
    @property
    def bytes_written(self):
        return self._bytes_written
    @property
    def write_io_count(self):
        return self._number_writes

class Path(object):
    @cached_method
    def get_connectivity(self):
        """
        Returns an `infi.storagemodel.connectivity.FCConnectivity` instance.
        """
        from ..connectivity import ConnectivityFactory
        return ConnectivityFactory.get_by_device_with_hctl(self)

    @cached_method
    def get_display_name(self):
        """ Returns the path name (currently the same as `get_path_id`)."""
        return self.get_path_id()

    #############################
    # Platform Specific Methods #
    #############################

    @cached_method
    def get_path_id(self):  # pragma: no cover
        """Returns depending on the operating system:

                    - sdX on linux
                    - PathId on Windows"""
        # platform implementation
        raise NotImplementedError()

    @cached_method
    def get_hctl(self):  # pragma: no cover
        """Returns a `infi.dtypes.hctl.HCTL` instance"""
        # platform implementation
        raise NotImplementedError()

    @cached_method
    def get_state(self):  # pragma: no cover
        """Returns either "up" or "down"."""
        # platform implementation
        raise NotImplementedError()

    def get_io_statistics(self):
        """Returns a `infi.storagemodel.base.multipath.PathStatistics` instance """
        raise NotImplementedError()

    def get_alua_state(self):
        """Returns the ALUA (Asymmetric Logical Unit Access) value"""
        raise NotImplementedError()

class ALUAState(object):

    ACTIVE_OPTIMIZED = 0
    ACTIVE_NON_OPTIMIZED = 1
    STANDBY = 2
    UNAVAILABLE = 3
