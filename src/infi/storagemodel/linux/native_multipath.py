from contextlib import contextmanager
from infi.storagemodel.base import multipath, gevent_wrapper
from infi.storagemodel.errors import StorageModelFindError, MultipathDaemonTimeoutError
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

    @contextmanager
    def asi_context(self):
        import os
        from infi.asi.unix import OSFile
        from infi.asi.linux import LinuxIoctlCommandExecuter

        handle = OSFile(os.open(self.get_block_access_path(), os.O_RDWR))
        executer = LinuxIoctlCommandExecuter(handle)
        executer.call = gevent_wrapper.defer(executer.call)
        try:
            yield executer
        finally:
            handle.close()

    def _is_there_atleast_one_path_up(self):
        return any(path.get_state() == "up" for path in self.get_paths())

    @cached_method
    def get_display_name(self):
        return self.multipath_object.device_name

    @cached_method
    def get_block_access_path(self):
        return "/dev/mapper/{}".format(self.multipath_object.device_name)

    @cached_method
    def get_device_mapper_access_path(self):
        return "/dev/{}".format(self.multipath_object.dm_name)

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

    @cached_method
    def get_scsi_vendor_id(self):
        try:
            return self.get_paths()[0].sysfs_device.get_vendor().strip()
        except:
            return super(LinuxNativeMultipathBlockDevice, self).get_scsi_vendor_id()

    @cached_method
    def get_scsi_revision(self):
        try:
            return self.get_paths()[0].sysfs_device.get_revision().strip()
        except:
            return super(LinuxNativeMultipathBlockDevice, self).get_scsi_revision()

    @cached_method
    def get_scsi_product_id(self):
        try:
            return self.get_paths()[0].sysfs_device.get_model().strip()
        except:
            return super(LinuxNativeMultipathBlockDevice, self).get_scsi_product_id()


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
        from infi.asi import create_platform_command_executer, create_os_file
        from .scsi import SG_TIMEOUT_IN_MS
        path = os.path.join("/dev", self.sysfs_device.get_scsi_generic_device_name())
        handle = create_os_file(path)
        executer = create_platform_command_executer(handle, timeout=SG_TIMEOUT_IN_MS)
        executer.call = gevent_wrapper.defer(executer.call)
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

    def get_io_statistics(self):
        # http://www.kernel.org/doc/Documentation/block/stat.txt
        stat_file_path = "/sys/block/{}/stat".format(self.get_path_id())
        with open(stat_file_path, "rb") as fd:
            stat_data = fd.read()
            stat_values = [int(val) for val in stat_data.split()]
            read_ios, _, read_sectors, _, write_ios, _, write_sectors, _, _, _, _ = stat_values
            # sector = always 512 bytes, not disk-dependent
            bytes_read = read_sectors * 512
            bytes_written = write_sectors * 512
            return multipath.PathStatistics(bytes_read, bytes_written, read_ios, write_ios)

class LinuxNativeMultipathModel(multipath.NativeMultipathModel):
    def __init__(self, sysfs):
        super(LinuxNativeMultipathModel, self).__init__()
        self.sysfs = sysfs

    def _is_device_active(self, multipath_device):
        return any(any(path.state == 'active' for path in group.paths) for group in multipath_device.path_groups)

    def _get_list_of_active_devices(self, client):
        from infi.multipathtools.errors import ConnectionError, TimeoutExpired
        from infi.exceptools import chain
        try:
            all_devices = client.get_list_of_multipath_devices()
            logger.debug("all multipath devices = {}".format(all_devices))
            active_devices = [device for device in all_devices if self._is_device_active(device)]
        except TimeoutExpired:
            logger.error("communication with multipathd timed out")
            return []
        except ConnectionError:
            logger.error("communication error with multipathd")
            return []
        return active_devices

    @cached_method
    def get_all_multipath_block_devices(self):
        from infi.multipathtools import MultipathClient
        from infi.multipathtools.connection import UnixDomainSocket
        client = MultipathClient(UnixDomainSocket(timeout=120))
        if not client.is_running():
            logger.warning("multipathd is not running")
            return []

        devices = self._get_list_of_active_devices(client)
        result = []
        logger.debug("Got {} devices from multipath client".format(len(devices)))
        for mpath_device in devices:
            block_dev = self.sysfs.find_block_device_by_devno(mpath_device.major_minor)
            if block_dev is not None:
                result.append(LinuxNativeMultipathBlockDevice(self.sysfs, block_dev, mpath_device))
        living_devices = [device for device in result if device._is_there_atleast_one_path_up()]
        return living_devices

    @cached_method
    def get_all_multipath_storage_controller_devices(self):
        return []
