
from infi.pyutils.lazy import cached_method, cached_property, LazyImmutableDict
from ..base import multipath
from ..errors import RescanIsNeeded
from .device_mixin import WindowsDeviceMixin, WindowsDiskDeviceMixin
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

MPIO_BUS_DRIVER_INSTANCE_ID = u"Root\\MPIO\\0000".lower()

class WindowsNativeMultipathModel(multipath.NativeMultipathModel):
    @cached_method
    def get_all_multipath_block_devices(self):
        from infi.devicemanager import DeviceManager
        from infi.wmpio import WmiClient, get_multipath_devices

        device_manager = DeviceManager()
        wmi_client = WmiClient()

        devices = filter(lambda device: device.parent._instance_id.lower() == MPIO_BUS_DRIVER_INSTANCE_ID,
                         device_manager.disk_drives)
        multipath_dict = get_multipath_devices(wmi_client)
        policies_dict = LazyLoadBalancingInfomrationDict(wmi_client)

        def _get_multipath_object(device_object):
            key = u"%s_0" % device_object._instance_id
            if not multipath_dict.has_key(key):
                raise RescanIsNeeded()
            return multipath_dict[key]

        def _get_multipath_device(device_object):
            return WindowsNativeMultipathBlockDevice(device_object, _get_multipath_object(device_object), policies_dict)

        return map(_get_multipath_device, devices)

    def filter_non_multipath_scsi_block_devices(self, scsi_block_devices):
        return filter(lambda device: device.get_parent()._instance_id != MPIO_BUS_DRIVER_INSTANCE_ID,
                         scsi_block_devices)

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
        active_paths = filter(lambda path: path.PrimaryPath == 1, policy.DSM_Paths)
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
    def get_block_access_path(self):
        return self.get_pdo()

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
        return HCTL(scsi_address.PortNumber, scsi_address.ScsiPathId, scsi_address.TargetId, scsi_address.Lun)

    @cached_method
    def get_state(self):
        return "up"

    @cached_method
    def get_display_name(self):
        return "%x" % self.get_path_id()

    def get_io_statistics(self):
        from infi.wmpio import get_device_performance, WmiClient
        wmi_client = WmiClient()
        device_wmi_path = self._multipath_object.InstanceName
        device_performance = get_device_performance(wmi_client)[device_wmi_path]
        path_perfromance = device_performance.PerfInfo[self.get_path_id()]
        return multipath.PathStatistics(path_perfromance.BytesRead,
                                        path_perfromance.BytesWritten,
                                        path_perfromance.NumberReads,
                                        path_perfromance.NumberWrites)