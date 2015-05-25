from infi.pyutils.lazy import cached_method
from infi.execute import execute_assert_success
from infi.dtypes.hctl import HCTL
from infi.storagemodel.base import gevent_wrapper
from infi.storagemodel.errors import StorageModelFindError, MultipathDaemonTimeoutError, DeviceError
from infi.storagemodel.base.scsi import SCSIModel, SCSIDevice, SCSIBlockDevice, SCSIStorageController
from contextlib import contextmanager
from logging import getLogger


logger = getLogger(__name__)


DIRECT_ACCESS_BLOCK_DEVICE = 0
STORAGE_ARRAY_CONTROLLER_DEVICE = 12


class AixSCSIDevice(SCSIDevice):
    def __init__(self, name):
        self._name = name

    @classmethod
    @cached_method
    def _get_adapter_to_host_mapping(cls):
        from infi.hbaapi import get_ports
        ports = get_ports()
        return {port.os_device_name: port.hct[0] for port in ports}

    @classmethod
    @cached_method
    def _get_host_by_driver(cls, driver_name):
        adapter = execute_assert_success(["/usr/sbin/lsdev", "-F", "parent", "-l", driver_name]).get_stdout().strip()
        mapping = cls._get_adapter_to_host_mapping()
        return mapping.get(adapter, -1)

    @contextmanager
    def asi_context(self):
        from infi.asi import create_platform_command_executer, create_os_file
        handle = create_os_file(self.get_scsi_access_path())
        executer = create_platform_command_executer(handle)
        executer.call = gevent_wrapper.defer(executer.call)
        try:
            yield executer
        finally:
            handle.close()

    @cached_method
    def get_hctl(self):
        """Returns a `infi.dtypes.hctl.HCTL` object"""
        driver = execute_assert_success(["/usr/sbin/lsdev", "-F", "parent", "-l", self._name]).get_stdout().strip()
        host = self._get_host_by_driver(driver)
        target, lun = execute_assert_success(["/usr/sbin/lsattr", "-F", "value", "-a", "ww_name", "-a", "lun_id",
            "-E", "-l", self._name]).get_stdout().strip().split("\n")
        target = int(target, 16)
        lun = int(lun, 16) >> 48
        return HCTL(host, 0, target, lun)

    @cached_method
    def get_display_name(self):
        """Returns a friendly device name"""
        return self._name

    @cached_method
    def get_scsi_access_path(self):
        """Returns a string path for the device"""
        return "/dev/" + self._name


class AixSCSIBlockDevice(AixSCSIDevice, SCSIBlockDevice):
    @cached_method
    def get_block_access_path(self):
        return self.get_scsi_access_path()


class AixSCSIStorageController(AixSCSIDevice, SCSIStorageController):
    pass


class AixModelMixin(object):
    def _get_dev_by_class(self, cls_name):
        proc = execute_assert_success(["/usr/sbin/lsdev", "-c", cls_name, "-F", "name"])
        output = proc.get_stdout().strip()
        if not output:
            return []
        return [line.strip() for line in output.split("\n")]

    def _get_multipath_devices(self):
        proc = execute_assert_success(["/usr/sbin/lspath", "-F", "name"])
        return set(proc.get_stdout().strip().split("\n"))

    def _is_disk_a_controller(self, dev):
        # AIX sometimes returns controller devices in 'lsdev -c disk' (instead of in 'lsdev -c dac') if the DOM
        # is not configured correctly (e.g. for INFINIDAT devices, the DOM can't be configured correctly because
        # INFINIDAT controllers don't have a unique product ID). So we must check the type in the inquiry data to
        # distinguish controllers and disks returned from 'lsdev -c disk'
        try:
            dev_type = dev.get_scsi_standard_inquiry().peripheral_device.type
            return dev_type == STORAGE_ARRAY_CONTROLLER_DEVICE
        except DeviceError:
            return None


class AixSCSIModel(SCSIModel, AixModelMixin):
    @cached_method
    def get_all_scsi_block_devices(self):
        """Returns a list of all `infi.storagemodel.aix.scsi.SCSIBlockDevice`."""
        disks = [AixSCSIBlockDevice(dev) for dev in self._get_dev_by_class("disk")]
        multipath_devices = self._get_multipath_devices()
        result = []
        for disk in disks:
            if disk.get_display_name() in multipath_devices:
                continue
            controller = self._is_disk_a_controller(disk)
            if controller is None or controller:     # controller or failed to determine
                continue
            result.append(disk)
        return result

    @cached_method
    def get_all_storage_controller_devices(self):
        """Returns a list of all `infi.storagemodel.aix.scsi.SCSIStorageController` objects."""
        controllers = [AixSCSIStorageController(dev) for dev in self._get_dev_by_class("dac")]
        disks = [AixSCSIStorageController(dev) for dev in self._get_dev_by_class("disk")]
        controllers.extend([disk for disk in disks if self._is_disk_a_controller(disk)])
        multipath_devices = self._get_multipath_devices()
        controllers = [controller for controller in controllers
                       if controller.get_display_name() not in multipath_devices]
        return controllers
