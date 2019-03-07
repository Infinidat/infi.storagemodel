
from infi.pyutils.lazy import cached_method, cached_property, LazyImmutableDict
from ..base import multipath
from ..errors import RescanIsNeeded
from .device_mixin import WindowsDeviceMixin, WindowsDiskDeviceMixin
from .device_helpers import is_disk_drive_managed_by_windows_mpio
from logging import getLogger
logger = getLogger(__name__)

# pylint: disable=W0212,E1002

class LazyLoadBalancingInfomrationDict(LazyImmutableDict):
    # Getting the load balancing information in Windows requires a seperate WQL call,
    # which is exepnsive. So we do not want to execute it unless the get_policy information is asked for
    # Fetching the get_policy information from WMI returns the information for all the devices,
    # not just for a specific one, so we must not execute it for every device
    # This is the mechanism I found suitable:
    # On the first call to the dict, it fetches the key and values from WMI and uses them from here on
    def __init__(self, wmi_client):
        # this (skipping the __init__ of LazyImmutableDict is on purpose
        super(LazyImmutableDict, self).__init__()
        self.wmi_client = wmi_client

    @cached_property
    def _dict(self):
        from infi.wmpio import get_load_balace_policies
        return get_load_balace_policies(self.wmi_client)


class WindowsNativeMultipathModel(multipath.NativeMultipathModel):
    @cached_method
    def get_all_multipath_block_devices(self):
        from infi.storagemodel.base.gevent_wrapper import run_together
        from infi.devicemanager import DeviceManager
        from infi.wmpio import WmiClient, get_multipath_devices
        from functools import partial
        device_manager = DeviceManager()
        wmi_client = WmiClient()
        physical_drives = set()

        multipath_dict = get_multipath_devices(wmi_client)
        policies_dict = LazyLoadBalancingInfomrationDict(wmi_client)

        def _get_multipath_object(device_object):
            prefix = u"%s_" % device_object._instance_id
            for key in multipath_dict:
                if key.startswith(prefix):
                    return multipath_dict[key]
            return None

        def _is_physical_drive(device_object):
            if device_object.get_physical_drive_number() != -1:
                physical_drives.add(device_object)

        def _iter_disk_drives():
            for disk_drive in device_manager.disk_drives:
                if not is_disk_drive_managed_by_windows_mpio(disk_drive):
                    logger.debug("disk drive {} is not managed by mpio".format(disk_drive))
                    continue
                multipath_object = _get_multipath_object(disk_drive)
                if multipath_object is None:
                    logger.error("no matching MPIO WMI instance found for disk drive {} (instance_id={!r})".format(disk_drive, disk_drive._instance_id))
                    continue
                yield WindowsNativeMultipathBlockDevice(disk_drive, multipath_object, policies_dict)

        run_together(partial(_is_physical_drive, drive) for drive in _iter_disk_drives())
        return list(physical_drives)

    def filter_non_multipath_scsi_block_devices(self, scsi_block_devices):
        return [device for device in scsi_block_devices if not is_disk_drive_managed_by_windows_mpio(device._device_object)]

    @cached_method
    def get_all_multipath_storage_controller_devices(self):
        return []

class WindowsFailoverOnly(multipath.FailoverOnly):
    def __init__(self, policy):
        active_path_id = None
        for path in policy.DSM_Paths:
            if path.PrimaryPath == 1:
                active_path_id = int(path.DsmPathId)
        super(WindowsFailoverOnly, self).__init__(active_path_id)

class WindowsRoundRobin(multipath.RoundRobin):
    pass

class WindowsRoundRobinWithSubset(multipath.RoundRobinWithSubset):
    def __init__(self, policy):
        active_paths = [path for path in policy.DSM_Paths if path.PrimaryPath == 1]
        active_path_ids = [path.DsmPathId for path in active_paths]
        super(WindowsRoundRobinWithSubset, self).__init__(active_path_ids)

class WindowsWeightedPaths(multipath.WeightedPaths):
    def __init__(self, wmpio_policy):
        weights = dict([(int(path.DsmPathId), int(path.PathWeight)) for path in wmpio_policy.DSM_Paths])
        super(WindowsWeightedPaths, self).__init__(weights)

class WindowsLeastBlocks(multipath.LeastBlocks):
    pass

class WindowsLeastQueueDepth(multipath.LeastQueueDepth):
    pass

class WindowsNativeMultipathBlockDevice(WindowsDiskDeviceMixin, WindowsDeviceMixin, multipath.MultipathBlockDevice):
    def __init__(self, device_object, multipath_object, policies_dict):
        super(WindowsNativeMultipathBlockDevice, self).__init__()
        self._device_object = device_object
        self._multipath_object = multipath_object
        self._policies_dict = policies_dict

    @cached_method
    def get_paths(self):
        return [WindowsPath(item, self._multipath_object) for item in self._multipath_object.PdoInformation]

    @cached_method
    def get_policy(self):
        from infi.wmpio.mpclaim import FAIL_OVER_ONLY, ROUND_ROBIN, ROUND_ROBIN_WITH_SUBSET, \
                                       WEIGHTED_PATHS, LEAST_BLOCKS, LEAST_QUEUE_DEPTH
        wmpio_policy = self._policies_dict["%s_0" % self.get_instance_id()]
        policy_number = wmpio_policy.LoadBalancePolicy
        if policy_number == FAIL_OVER_ONLY:
            return WindowsFailoverOnly(wmpio_policy)
        if policy_number == ROUND_ROBIN:
            return WindowsRoundRobin()
        if policy_number == ROUND_ROBIN_WITH_SUBSET:
            return WindowsRoundRobinWithSubset(wmpio_policy)
        if policy_number == WEIGHTED_PATHS:
            return WindowsWeightedPaths(wmpio_policy)
        if policy_number == LEAST_BLOCKS:
            return WindowsLeastBlocks()
        if policy_number == LEAST_QUEUE_DEPTH:
            return WindowsLeastQueueDepth()

class WindowsPath(multipath.Path):
    def __init__(self, pdo_information, multipath_object):
        super(WindowsPath, self).__init__()
        self._pdo_information = pdo_information
        self._multipath_object = multipath_object

    @cached_method
    def get_path_id(self):
        return int(self._pdo_information.PathIdentifier)

    @cached_method
    def get_hctl(self):
        from infi.dtypes.hctl import HCTL
        scsi_address = self._pdo_information.ScsiAddress
        try:
            return HCTL(scsi_address.PortNumber, scsi_address.ScsiPathId, scsi_address.TargetId, scsi_address.Lun)
        except AttributeError:
            # we lost a PDO
            raise RescanIsNeeded()

    @cached_method
    def get_state(self):
        return "up"

    @cached_method
    def get_display_name(self):
        return "%x" % self.get_path_id()

    def get_io_statistics(self):
        from infi.wmpio import get_device_performance, get_multipath_devices, WmiClient
        wmi_client = WmiClient()
        device_wmi_path = self._multipath_object.InstanceName
        all_performance_counters = get_device_performance(wmi_client)
        all_devices = get_multipath_devices(wmi_client)
        if device_wmi_path not in all_performance_counters:
            logger.warn('no perfomance countrs for device {}'.format(device_wmi_path), exc_info=1)
            return multipath.PathStatistics(0, 0, 0, 0)
        device_performance = all_performance_counters[device_wmi_path]
        path_perfromance = device_performance.PerfInfo[self.get_path_id()]
        return multipath.PathStatistics(path_perfromance.BytesRead,
                                        path_perfromance.BytesWritten,
                                        path_perfromance.NumberReads,
                                        path_perfromance.NumberWrites)

    def get_alua_state(self):
        from infi.wmpio.wmi import WmiClient
        from infi.wmpio.wmi import get_load_balace_policies
        load_balance_policies = get_load_balace_policies(WmiClient())
        for path in load_balance_policies[self._multipath_object.InstanceName].DSM_Paths:
            if int(path.DsmPathId) == self.get_path_id():
                return path.TargetPortGroup_State
