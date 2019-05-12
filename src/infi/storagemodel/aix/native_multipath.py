from infi.execute import execute_assert_success
from infi.pyutils.lazy import cached_method
from infi.dtypes.hctl import HCTL
from infi.storagemodel.base import gevent_wrapper
from contextlib import contextmanager
from infi.storagemodel.unix.multipath import UnixPathMixin
from infi.storagemodel.base.multipath import MultipathFrameworkModel, MultipathStorageController, MultipathBlockDevice
from infi.storagemodel.base.multipath import Path, PathStatistics, LeastQueueDepth, FailoverOnly, RoundRobin
from .scsi import AixModelMixin, AixSCSIDevice


class AixFailover(FailoverOnly):
    """fail_over:      I/O is routed to one path at a time. If if fails next enabled path is selected. (Path priority determines which path is next)"""
    name = "fail_over"
    def __init__(self):
        super(AixFailover, self).__init__(None)


class AixRoundRobin(RoundRobin):
    """round_robin:    I/O is distributed to all enabled paths. Paths with same prio. has equal I/O, otherwise higher prio. has higher % of I/O.)"""
    name = "round_robin"


class AixShortestQueue(LeastQueueDepth):
    """shortest_queue: Similar to round_robin, but when load increases it favors path with fewest active I/O operations. Path priority is ignored."""
    name = "shortest_queue"


class AixPath(Path):
    def __init__(self, mpio_device_name, path_id, driver, target, lun, status):
        self._mpio_device_name = mpio_device_name
        self._path_id = path_id
        self._driver = driver
        self._target = target
        self._lun = lun
        self._status = status

    @cached_method
    def get_path_id(self):
        """Returns depending on the operating system"""
        return self._path_id

    @cached_method
    def get_hctl(self):
        """Returns a `infi.dtypes.hctl.HCTL` instance"""
        host = AixSCSIDevice._get_host_by_driver(self._driver)
        return HCTL(host, 0, self._target, self._lun)

    @cached_method
    def get_state(self):
        """Returns either "up" or "down"."""
        return "up" if self._status == "Enabled" else "down"

    def get_io_statistics(self):
        """Returns a `infi.storagemodel.base.multipath.PathStatistics` instance """
        proc = execute_assert_success(["iostat", "-m", self._mpio_device_name])
        lines = proc.get_stdout().decode().strip().split("\n")
        path_line = [line for line in lines if line.startswith("Path{}".format(self._path_id))][0]
        path, tm_act, kbps, tps, kb_read, kb_wrtn = path_line.split()
        # iostat doesn't return the nubmer of reads/writes, but each read and write uses an entire block
        # (4k), so if we divide kb_read/kb_wrtn by 4 we'll get the number
        return PathStatistics(int(kb_read) * 1024, int(kb_wrtn) * 1024, int(kb_read) / 4, int(kb_wrtn) / 4)


class AixMultipathMixin(object):
    def __init__(self, name):
        self._name = name

    @contextmanager
    def asi_context(self):
        from infi.asi import create_platform_command_executer, create_os_file
        handle = create_os_file(self._get_access_path())
        executer = create_platform_command_executer(handle)
        executer.call = gevent_wrapper.defer(executer.call)
        try:
            yield executer
        finally:
            handle.close()

    @cached_method
    def get_display_name(self):
        """Returns a friendly device name"""
        return self._name

    @cached_method
    def get_paths(self):
        """Returns a list of `infi.storagemodel.base.multipath.Path` instances"""
        proc = execute_assert_success(["/usr/sbin/lspath", "-F", "path_id,parent,connection,status", "-l", self._name])
        lines = proc.get_stdout().decode().strip().split("\n")
        result = []
        for line in lines:
            if line.count(",") == 4:
                path_id, driver, target, lun, status = line.split(",")
            else:
                # non-FC disks may not have two values for "connection".
                # still treat the connection as the target and emulate the LUN
                path_id, driver, target, status = line.split(",")
                lun = "0"
            target = int(target, 16)
            lun = int(lun, 16) >> 48
            result.append(AixPath(self._name, path_id, driver, target, lun, status))
        return result

    @cached_method
    def get_policy(self):
        """Returns an instance of `infi.storagemodel.base.multipath.LoadBalancePolicy`"""
        proc = execute_assert_success(["/usr/sbin/lsattr", "-F", "value", "-a", "algorithm", "-l", self._name])
        value = proc.get_stdout().decode().strip()
        return next((policy for policy in (AixFailover, AixRoundRobin, AixShortestQueue) if policy.name == value))()

    def _get_access_path(self):
        return "/dev/" + self._name


class AixMultipathBlockDevice(AixMultipathMixin, MultipathBlockDevice):
    @cached_method
    def get_block_access_path(self):
        """Returns a path for the device"""
        return self._get_access_path()


class AixMultipathStorageController(AixMultipathMixin, MultipathStorageController):
    @cached_method
    def get_multipath_access_path(self):
        """Returns a string path for the device"""
        return self._get_access_path()


class AixNativeMultipathModel(MultipathFrameworkModel, AixModelMixin):
    @cached_method
    def get_all_multipath_block_devices(self):
        """Returns a list of all `infi.storagemodel.aix.scsi.SCSIBlockDevice`."""
        disks = [AixMultipathBlockDevice(dev) for dev in self._get_dev_by_class("disk")]
        multipath_devices = self._get_multipath_devices()
        result = []
        for disk in disks:
            if disk.get_display_name() not in multipath_devices:
                continue
            controller = self._is_disk_a_controller(disk)
            if controller is None or controller:     # controller or failed to determine
                continue
            result.append(disk)
        return result

    @cached_method
    def get_all_multipath_storage_controller_devices(self):
        """Returns a list of all `infi.storagemodel.aix.scsi.SCSIStorageController` objects."""
        controllers = [AixMultipathStorageController(dev) for dev in self._get_dev_by_class("dac")]
        disks = [AixMultipathStorageController(dev) for dev in self._get_dev_by_class("disk")]
        controllers.extend([disk for disk in disks if self._is_disk_a_controller(disk)])
        multipath_devices = self._get_multipath_devices()
        controllers = [controller for controller in controllers
                       if controller.get_display_name() in multipath_devices]
        return controllers

    def filter_non_multipath_scsi_block_devices(self, scsi_block_devices):
        """Returns items from the list that are not part of multipath devices claimed by this framework"""
        return scsi_block_devices  # no co-existence

    def filter_non_multipath_scsi_storage_controller_devices(self, scsi_controller_devices):
        """Returns items from the list that are not part of multipath devices claimed by this framework"""
        return scsi_controller_devices  # no co-existence
