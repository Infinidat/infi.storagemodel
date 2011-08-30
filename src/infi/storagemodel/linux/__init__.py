import itertools
from contextlib import contextmanager

from ..base import StorageModel, scsi, multipath
from ..errors import StorageModelFindError
from infi.pyutils.lazy import cached_method

from .sysfs import Sysfs

class LinuxBlockDeviceMixin(object):
    @cached_method
    def get_block_access_path(self):
        return "/dev/%s" % self.sysfs_device.get_block_device_name()

    @cached_method
    def get_unix_block_devno(self):
        return self.sysfs_device.get_block_devno()

    @cached_method
    def get_size_in_bytes(self):
        return self.sysfs_device.get_size_in_bytes()

class LinuxSCSIDeviceMixin(object):
    @contextmanager
    def asi_context(self):
        import os
        from infi.asi.unix import OSFile
        from infi.asi import create_platform_command_executer

        handle = OSFile(os.open(self.get_scsi_access_path(), os.O_RDWR))
        executer = create_platform_command_executer(handle)
        try:
            yield executer
        finally:
            handle.close()

    @cached_method
    def get_hctl(self):
        return self.sysfs_device.get_hctl()

    @cached_method
    def get_scsi_access_path(self):
        return "/dev/%s" % self.sysfs_device.get_scsi_generic_device_name()

    @cached_method
    def get_linux_scsi_generic_devno(self):
        return self.sysfs_device.get_scsi_generic_devno()

class LinuxSCSIBlockDeviceMixin(LinuxSCSIDeviceMixin, LinuxBlockDeviceMixin):
    pass

class LinuxSCSIBlockDevice(LinuxSCSIBlockDeviceMixin, scsi.SCSIBlockDevice):
    def __init__(self, sysfs_device):
        super(LinuxSCSIBlockDevice, self).__init__()
        self.sysfs_device = sysfs_device

    @cached_method
    def get_display_name(self):
        return self.sysfs_device.get_block_device_name()

class LinuxSCSIStorageController(LinuxSCSIDeviceMixin, scsi.SCSIStorageController):
    def __init__(self, sysfs_device):
        super(LinuxSCSIStorageController, self).__init__()
        self.sysfs_device = sysfs_device

    @cached_method
    def get_display_name(self):
        return self.sysfs_device.get_scsi_generic_device_name()

class LinuxSCSIModel(scsi.SCSIModel):
    def __init__(self, sysfs):
        self.sysfs = sysfs

    @cached_method
    def get_all_scsi_block_devices(self):
        return [ LinuxSCSIBlockDevice(sysfs_disk) for sysfs_disk in self.sysfs.get_all_scsi_disks() ]

    @cached_method
    def get_all_storage_controller_devices(self):
        return [ LinuxSCSIStorageController(sysfs_dev) for sysfs_dev in self.sysfs.get_all_scsi_storage_controllers() ]

    def find_scsi_block_device_by_block_devno(self, devno):
        devices = [ dev for dev in self.get_all_scsi_block_devices() if dev.get_unix_block_devno() == devno ]
        if len(devices) != 1:
            raise StorageModelFindError("%d SCSI block devices found with devno=%s" % (len(devices), devno))
        return devices[0]

class LinuxNativeMultipathDevice(LinuxBlockDeviceMixin, multipath.MultipathDevice):
    def __init__(self, sysfs, sysfs_device, multipath_object):
        super(LinuxNativeMultipathDevice, self).__init__()
        self.sysfs = sysfs
        self.sysfs_device = sysfs_device
        self.multipath_object = multipath_object

    def asi_context(self):
        for path in self.get_paths():
            if path.get_state() == "up":
                return path.asi_context()
        raise StorageModelError("cannot find an active path to open SCSI generic device")

    @cached_method
    def get_display_name(self):
        return self.multipath_object.device_name

    @cached_method
    def get_device_access_path(self):
        return self.get_block_access_path()
    
    @cached_method
    def get_paths(self):
        return list(LinuxPath(self.sysfs, path) for path in \
                    itertools.chain.from_iterable(group.paths for group in self.multipath_object.path_groups))
    
    @cached_method
    def get_policy(self):
        # TODO implement
        pass

class LinuxPath(multipath.Path):
    def __init__(self, sysfs, multipath_object_path):
        from infi.dtypes.hctl import HCTL
        self.multipath_object_path = multipath_object_path
        self.hctl = HCTL(*self.multipath_object_path.hctl)
        self.sysfs_device = sysfs.find_scsi_disk_by_hctl(self.hctl)

    @contextmanager
    def asi_context(self):
        import os
        from infi.asi.unix import OSFile
        from infi.asi import create_platform_command_executer

        handle = OSFile(os.open(os.path.join("/dev", self.sysfs_device.get_scsi_generic_device_name()), os.O_RDWR))
        executer = create_platform_command_executer(handle)
        try:
            yield executer
        finally:
            handle.close()
        
    @cached_method
    def get_path_id(self):
        return self.multipath_object_path.device_name
        
    def get_hctl(self):
        return self.hctl

    @cached_method
    def get_state(self):
        return "up" if self.multipath_object_path.state == "active" else "down"
    
class LinuxNativeMultipathModel(multipath.NativeMultipathModel):
    def __init__(self, sysfs):
        super(LinuxNativeMultipathModel, self).__init__()
        self.sysfs = sysfs
        
    @cached_method
    def get_all_multipath_devices(self):
        from infi.multipathtools import MultipathClient
        client = MultipathClient()
        devices = client.get_list_of_multipath_devices()

        result = []
        for mpath_device in devices:
            block_dev = self.sysfs.find_block_device_by_devno(mpath_device.major_minor)
            if block_dev is not None:
                result.append(LinuxNativeMultipathDevice(self.sysfs, block_dev, mpath_device))
            
        return result

RESCAN_SCRIPT_NAME = "rescan-scsi-bus.sh"

class LinuxStorageModel(StorageModel):
    @cached_method
    def _get_sysfs(self):
        return Sysfs()
    
    def _create_scsi_model(self):
        return LinuxSCSIModel(self._get_sysfs())

    def _create_native_multipath_model(self):
        return LinuxNativeMultipathModel(self._get_sysfs())

    def _call_rescan_script(self, env=None):
        """for testability purposes, we want to call execute with no environment variables, to mock the effect
        that the script does not exist"""
        from infi.exceptools import chain
        from infi.execute import execute
        from ..errors import StorageModelError
        try:
            _ = execute([RESCAN_SCRIPT_NAME, "--remove"], env=env)
        except:
            raise chain(StorageModelError("failed to initiate rescan"))

    def initiate_rescan(self):
        """the first attempt will be to use rescan-scsi-bus.sh, which comes out-of-the-box in redhat distributions,
        and from the debian packager scsitools.
        If and when we'll encounter a case in which this script doesn't work as expected, we will port it to Python
        and modify it accordingly.
        """
        self._call_rescan_script()

def is_rescan_script_exists():
    from os import environ, pathsep
    from os.path import exists, join
    return any([exists(join(dirpath, RESCAN_SCRIPT_NAME)) for dirpath in environ["PATH"].split(pathsep)])
