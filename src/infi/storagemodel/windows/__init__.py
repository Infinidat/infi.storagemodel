
from ..utils import cached_method, cached_property, clear_cache
from infi.storagemodel.base import SCSIBlockDevice, SCSIDevice, StorageModel, MultipathDevice, SCSIStorageController, \
    SCSIModel, NativeMultipathModel, Path
from contextlib import contextmanager
from infi.storagemodel.utils import LazyImmutableDict
from infi.storagemodel.base import multipath

class WindowsDeviceMixin(object):
    @cached_property
    def pdo(self):
        return self._device_object.psuedo_device_object

    @contextmanager
    def asi_context(self):
        from infi.asi.win32 import OSFile
        from infi.asi import create_platform_command_executer
        handle = OSFile(self.scsi_access_path)
        executer = create_platform_command_executer(handle)
        try:
            yield executer
        finally:
            handle.close()

    @cached_property
    def ioctl_interface(self):
        from infi.devicemanager.ioctl import DeviceIoControl
        return DeviceIoControl(self.scsi_access_path)

    @cached_property
    def instance_id(self):
        return self._device_object._instance_id

class WindowsSCSIDevice(WindowsDeviceMixin, SCSIDevice):
    def __init__(self, device_object):
        super(WindowsSCSIDevice, self).__init__()
        self._device_object = device_object

    @cached_property
    def scsi_vendor_id(self):
        # a faster implemntation on windows
        return self._device_object.hardware_ids[-2][0:8].replace('_', '')

    @cached_property
    def scsi_product_id(self):
        # a faster implementation on windows
        return self._device_object.hardware_ids[-2][8:24].replace('_', '')

    @cached_property
    def hctl(self):
        from ..dtypes import HCTL
        return self.ioctl_interface.scsi_get_address()

    @cached_property
    def block_access_path(self):
        return self.pdo

    @cached_property
    def scsi_access_path(self):
        return self.pdo

    @cached_property
    def display_name(self):
        return self.scsi_access_path.split('\\')[-1]

class WindowsDiskDeviceMixin(object):
    @cached_property
    def size_in_bytes(self):
        return self.ioctl_interface.disk_get_length_info()

    @cached_property
    def physical_drive_number(self):
        """returns the drive number of the disk.
        if the disk is hidden (i.e. part of MPIODisk), it returns -1
        """
        number = self.ioctl_interface.storage_get_device_number()
        return -1 if number == 0xffffffff else number

    @cached_property
    def display_name(self):
        return "PHYSICALDRIVE%s" % self.physical_drive_number

class WindowsSCSIBlockDevice(WindowsDiskDeviceMixin, WindowsSCSIDevice, SCSIBlockDevice):
    pass

class WindowsSCSIStorageController(WindowsSCSIDevice, SCSIStorageController):
    def __init__(self, device_object):
        super(WindowsSCSIStorageController, self).__init__()
        self._device_object = device_object

class WindowsSCSIModel(SCSIModel):
    @cached_property
    def device_manager(self):
        from infi.devicemanager import DeviceManager
        return DeviceManager()

    @cached_method
    def get_all_scsi_block_devices(self):
        return filter(lambda disk: disk.physical_drive_number != -1,
                      [WindowsSCSIBlockDevice(device) for device in self.device_manager.disk_drives])

    @cached_method
    def get_all_storage_controller_devices(self):
        from infi.devicemanager.setupapi.constants import SYSTEM_DEVICE_GUID_STRING
        # Stoage controllers are listed under the SCSI Adapters and their CLASSGUID is this
        # Unless there are some other SCSI devices that have this GUID (afaik there aren't)
        # this is good enough
        return filter(lambda device: device.class_guid == SYSTEM_DEVICE_GUID_STRING,
                      [WindowsSCSIStorageController(device) for device in self.device_manager.scsi_devices])

class LazyLoadBalancingInfomrationDict(LazyImmutableDict):
    # Getting the load balancing information in Windows requires a seperate WQL call,
    # which is exepnsive. So we do not want to execute it unless the policy information is asked for
    # Fetching the policy information from WMI returns the information for all the devices,
    # not just for a specific one, so we must not execute it for every device
    # This is the mechanism I found suitable:
    # On the first call to the dict, it fetches the key and values from WMI and uses them from here on
    def __init__(self, wmi_client):
        super(LazyImmutableDict, self).__init__()
        self.wmi_client = wmi_client

    @cached_property
    def _dict(self):
        from infi.wmpio import get_load_balace_policies
        return get_load_balace_policies(self.wmi_client)

MPIO_BUS_DRIVER_INSTANCE_ID = u"Root\\MPIO\\0000"

class WindowsNativeMultipathModel(NativeMultipathModel):
    @cached_method
    def get_all_multipath_devices(self):
        from infi.devicemanager import DeviceManager
        from infi.wmpio import WmiClient, get_multipath_devices

        device_manager = DeviceManager()
        wmi_client = WmiClient()

        devices = filter(lambda device: device.parent._instance_id == MPIO_BUS_DRIVER_INSTANCE_ID,
                         device_manager.disk_drives)
        multipath_dict = get_multipath_devices(wmi_client)
        policies_dict = LazyLoadBalancingInfomrationDict(wmi_client)
        return [WindowsNativeMultipathDevice(device_object,
                                       multipath_dict[u"%u_0" % device_object._instance_id],
                                       policies_dict) for device_object in devices]

    def filter_non_multipath_scsi_block_devices(self, scsi_block_devices):
        devices = filter(lambda device: device.parent._instance_id != MPIO_BUS_DRIVER_INSTANCE_ID,
                         scsi_block_devices)

class WindowsNativeMultipathLoadBalancingContext(multipath.LoadBalancingContext):
    def __init__(self, policies_dict):
        super(WindowsNativeMultipathLoadBalancingContext, self).__init__()
        self._policies_dict = policies_dict

    def get_policy_for_device(self, device):
        from infi.wmpio.mpclaim import FAIL_OVER_ONLY, ROUND_ROBIN, ROUND_ROBIN_WITH_SUBSET, \
                                       WEIGHTED_PATHS, LEAST_BLOCKS, LEAST_QUEUE_DEPTH
        wmpio_policy = self._policies_dict[device.instance_id]
        policy_number = wmpio_policy.LoadBalancePolicy
        if policy_number == FAIL_OVER_ONLY:
            return WindowsFailoverOnly()
        if policy_number == ROUND_ROBIN:
            return WindowsRoundRobin()
        if policy_number == ROUND_ROBIN_WITH_SUBSET:
            return WindowsRoundRobinWithSubset(device)
        if policy_number == WEIGHTED_PATHS:
            return WindowsWeightedPaths(wmpio_policy)
        if policy_number == LEAST_BLOCKS:
            return WindowsLeastBlocks()
        if policy_number == LEAST_QUEUE_DEPTH:
            return WindowsLeastQueueDepth()

class WindowsFailoverOnly(multipath.FailoverOnly):
    pass

class WindowsRoundRobin(multipath.RoundRobin):
    pass

class WindowsRoundRobinWithSubset(multipath.RoundRobinWithSubset):
    def __init__(self, device):
        active_paths = filter(lambda path: path.device_state == 1, device.paths)
        active_path_ids = [path.PathIdentifier for path in active_paths]
        super(WindowsRoundRobinWithSubset, self).__init__(active_path_ids)

class WindowsWeightedPaths(multipath.WeightedPaths):
    def __init__(self, wmpio_policy):
        weights = dict([(path.DsmPathId, path.PathWeight) for path in wmpio_policy.Dsm_Paths])
        super(WindowsWeightedPaths, self).__init__(weights)

class WindowsLeastBlocks(multipath.LeastBlocks):
    pass

class WindowsLeastQueueDepth(multipath.LeastQueueDepth):
    pass

class WindowsNativeMultipathDevice(WindowsDiskDeviceMixin, WindowsDeviceMixin, MultipathDevice):
    def __init__(self, device_object, multipath_object, policies_dict):
        super(WindowsNativeMultipathDevice, self).__init__()
        self._device_object = device_object
        self._multipath_object = multipath_object
        self._policies_dict = policies_dict

    @cached_property
    def device_access_path(self):
        return self.pdo

    @cached_property
    def paths(self):
        return [WindowsPath(item) for item in self._multipath_object.PdoInformation]

    @cached_property
    def _platform_specific_policy_context(self):
        return WindowsNativeMultipathLoadBalancingContext(self._policies_dict)

class WindowsPath(Path):
    def __init__(self, pdo_information):
        super(WindowsPath, self).__init__()
        self._pdo_information = pdo_information

    @cached_property
    def path_id(self):
        return self._pdo_information.PathIdentifier

    @cached_property
    def hctl(self):
        from ..dtypes import HCTL
        scsi_address = self._pdo_information.ScsiAddress
        return HCTL(scsi_address.PortNumber, scsi_address.ScsiPathId, scsi_address.TargetId, scsi_address.Lun)

    @cached_property
    def state(self):
        return "up"

class WindowsStorageModel(StorageModel):
    def _create_scsi_model(self):
        return WindowsSCSIModel()

    def _create_native_multipath_model(self):
        return WindowsNativeMultipathModel()
