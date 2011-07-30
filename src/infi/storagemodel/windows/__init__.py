
from ..utils import cached_method, cached_property, clear_cache
from infi.storagemodel.base import SCSIBlockDevice, SCSIDevice, StorageModel, MultipathDevice, SCSIStorageController, \
    ScsiModel, NativeMultipathModel, Path
from contextlib import contextmanager
from infi.storagemodel.utils import LazyImmutableDict

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

class WindowsSCSIModel(ScsiModel):
    @cached_method
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
        return [WindowsMultipathDevice(device_object,
                                       multipath_dict[u"%u_0" % device_object._instance_id],
                                       policies_dict) for device_object in devices]

    def filter_non_multipath_scsi_block_devices(self, scsi_block_devices):
        devices = filter(lambda device: device.parent._instance_id != MPIO_BUS_DRIVER_INSTANCE_ID,
                         scsi_block_devices)

class WindowsMultipathDevice(WindowsDiskDeviceMixin, WindowsDeviceMixin, MultipathDevice):
    def __init__(self, device_object, multipath_object, policies_dict):
        super(WindowsMultipathDevice, self).__init__()
        self._device_object = device_object
        self._multipath_object = multipath_object
        self._policy_object = policies_dict

    @cached_property
    def device_access_path(self):
        return self.pdo

    def paths(self):
        raise NotImplementedError

    def policy(self):
        raise NotImplementedError

    def policy_attributes(self):
        raise NotImplementedError

    def apply_policy(self, policy_builder):
        raise NotImplementedError

class WindowsStorageModel(StorageModel):
    def _create_scsi_model(self):
        return WindowsSCSIModel()

    def _create_native_multipath(self):
        return WindowsNativeMultipathModel()

