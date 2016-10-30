from infi.storagemodel.unix.veritas_multipath import VeritasMultipathClient
from infi.storagemodel.base import multipath, gevent_wrapper
from infi.pyutils.lazy import cached_method
from contextlib import contextmanager

from logging import getLogger
logger = getLogger(__name__)


class LinuxVeritasMultipathBlockDevice(multipath.MultipathBlockDevice):
    def __init__(self, sysfs, scsi, multipath_object):
        super(LinuxVeritasMultipathBlockDevice, self).__init__()
        self.multipath_object = multipath_object
        self._sysfs = sysfs
        self._scsi = scsi

    def _is_there_atleast_one_path_up(self):
        return any(path.get_state() == "up" for path in self.get_paths())

    @cached_method
    def get_display_name(self):
        return self.multipath_object.dmp_name

    @cached_method
    def get_block_access_path(self):
        return "/dev/vx/dmp/{}".format(self.multipath_object.dmp_name)

    @cached_method
    def get_paths(self):
        paths = list()
        for path in self.multipath_object.paths:
            try:
                paths.append(VeritasPath(self._sysfs, self._scsi, path))
            except (ValueError, KeyError):
                logger.debug("VeritasPath sysfs device disappeared for {}".format(path))
        return paths

    @cached_method
    def get_policy(self):
        raise NotImplementedError() # TODO

    @cached_method
    def get_disk_drive(self):  # pragma: no cover
        raise NotImplementedError

    @cached_method
    def get_scsi_vendor_id(self):
        try:
            return self.get_paths()[0].sysfs_device.get_vendor().strip()
        except:
            return super(LinuxVeritasMultipathBlockDevice, self).get_scsi_vendor_id()

    @cached_method
    def get_scsi_revision(self):
        try:
            return self.get_paths()[0].sysfs_device.get_revision().strip()
        except:
            return super(LinuxVeritasMultipathBlockDevice, self).get_scsi_revision()

    @cached_method
    def get_scsi_product_id(self):
        try:
            return self.get_paths()[0].sysfs_device.get_model().strip()
        except:
            return super(LinuxVeritasMultipathBlockDevice, self).get_scsi_product_id()

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

    @cached_method
    def get_size_in_bytes(self):
        from fcntl import ioctl
        from struct import unpack
        BLKGETSIZE64 = 0x80081272
        block_device = open(self.get_block_access_path())
        size = ioctl(block_device, BLKGETSIZE64, '\x00\x00\x00\x00\x00\x00\x00\x00')
        return unpack('L', size)[0]


class VeritasPath(multipath.Path):
    def __init__(self, sysfs, scsi_model, multipath_object_path):
        self._sysfs = sysfs
        self._scsi_model = scsi_model
        self.multipath_object_path = multipath_object_path
        block_access_path = '/dev/{}'.format(self.multipath_object_path.sd_device_name)
        self.hctl = self._scsi_model.find_scsi_block_device_by_block_access_path(block_access_path).get_hctl()
        self.sysfs_device = sysfs.find_scsi_disk_by_hctl(self.hctl)

    @cached_method
    def get_path_id(self):
        return self.multipath_object_path.sd_device_name

    def get_hctl(self):
        return self.hctl

    @cached_method
    def get_state(self):
        return "up" if "enabled" in self.multipath_object_path.state else "down"

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


class LinuxVeritasMultipathModel(multipath.VeritasMultipathModel):
    def __init__(self, sysfs, scsi):
        super(LinuxVeritasMultipathModel, self).__init__()
        self._sysfs = sysfs
        self._scsi = scsi

    def _is_device_active(self, multipath_device):
        return any('enabled' in path.state for path in multipath_device.paths)

    def _get_list_of_active_devices(self, client):
        all_devices = client.get_list_of_multipath_devices()
        logger.debug("all multipath devices = {}".format(all_devices))
        active_devices = [device for device in all_devices if self._is_device_active(device)]
        return active_devices

    @cached_method
    def get_all_multipath_block_devices(self):
        client = VeritasMultipathClient()
        devices = self._get_list_of_active_devices(client)
        logger.debug("Got {} devices from multipath client".format(len(devices)))
        result = [LinuxVeritasMultipathBlockDevice(self._sysfs, self._scsi, d) for d in devices]
        return [d for d in result if d._is_there_atleast_one_path_up()]

    @cached_method
    def get_all_multipath_storage_controller_devices(self):
        return []
