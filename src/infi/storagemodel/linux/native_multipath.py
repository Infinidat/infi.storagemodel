from contextlib import contextmanager
from ..base import multipath
from ..errors import StorageModelFindError, MultipathDaemonTimeoutError
from infi.pyutils.lazy import cached_method
from .block import LinuxBlockDeviceMixin
import itertools

from logging import getLogger
logger = getLogger(__name__)

class LinuxNativeMultipathBlockDevice(LinuxBlockDeviceMixin, multipath.MultipathBlockDevice):
    def __init__(self, sysfs, sysfs_device, multipath_object):
        super(LinuxNativeMultipathBlockDevice, self).__init__()
        self.sysfs = sysfs
        self.sysfs_device = sysfs_device
        self.multipath_object = multipath_object

    def asi_context(self):
        for path in self.get_paths():
            if path.get_state() == "up":
                return path.asi_context()
        raise StorageModelFindError("cannot find an active path to open SCSI generic device") # pylint: disable=W0710

    def _is_there_atleast_one_path_up(self):
        return bool(filter(lambda path: path.get_state() == "up", self.get_paths()))

    @cached_method
    def get_display_name(self):
        return self.sysfs_device.block_device_name

    @cached_method
    def get_block_access_path(self):
        return "/dev/mapper/{}".format(self.multipath_object.device_name)

    @cached_method
    def get_paths(self):
        paths = list()
        for path in itertools.chain.from_iterable(group.paths for group in self.multipath_object.path_groups):
            try:
                paths.append(LinuxPath(self.sysfs, path))
            except ValueError:
                logger.debug("LinuxPath sysfs device disappeared for {}".format(path))
        return paths

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

    def _is_device_active(self, multipath_device):
        return any([any([path.state == 'active' for path in group.paths]) for group in multipath_device.path_groups])

    def _get_list_of_active_devices(self, client):
        from infi.multipathtools.errors import ConnectionError, TimeoutExpired
        from infi.exceptools import chain
        try:
            devices = [device for device in client.get_list_of_multipath_devices() if self._is_device_active(device)]
        except TimeoutExpired:
            raise chain(MultipathDaemonTimeoutError())
        except ConnectionError:
            raise chain(StorageModelFindError())
        return devices

    @cached_method
    def get_all_multipath_block_devices(self):
        from infi.multipathtools import MultipathClient
        client = MultipathClient()
        if not client.is_running():
            logger.info("MultipathD is not running")
            return []

        devices = self._get_list_of_active_devices(client)
        result = []
        logger.debug("Got {} devices from multipath client".format(len(devices)))
        for mpath_device in devices:
            block_dev = self.sysfs.find_block_device_by_devno(mpath_device.major_minor)
            if block_dev is not None:
                result.append(LinuxNativeMultipathBlockDevice(self.sysfs, block_dev, mpath_device))
        living_devices = filter(lambda device: device._is_there_atleast_one_path_up(), result)
        return living_devices

    @cached_method
    def get_all_multipath_storage_controller_devices(self):
        return []
