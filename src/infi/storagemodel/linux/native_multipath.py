from contextlib import contextmanager
from ..base import multipath
from ..errors import StorageModelFindError
from infi.pyutils.lazy import cached_method
from .block import LinuxBlockDeviceMixin
import itertools

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
        raise StorageModelFindError("cannot find an active path to open SCSI generic device") # pylint: disable=W0710

    @cached_method
    def get_display_name(self):
        return self.multipath_object.device_name

    @cached_method
    def get_block_access_path(self):
        return self.get_block_access_path()

    @cached_method
    def get_paths(self):
        return list(LinuxPath(self.sysfs, path) for path in \
                    itertools.chain.from_iterable(group.paths for group in self.multipath_object.path_groups))

    @cached_method
    def get_policy(self):
        return LinuxRoundRobin()

class LinuxRoundRobin(multipath.RoundRobin):
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
        if not client.is_running():
            return []
        devices = client.get_list_of_multipath_devices()

        result = []
        for mpath_device in devices:
            block_dev = self.sysfs.find_block_device_by_devno(mpath_device.major_minor)
            if block_dev is not None:
                result.append(LinuxNativeMultipathDevice(self.sysfs, block_dev, mpath_device))

        return result
