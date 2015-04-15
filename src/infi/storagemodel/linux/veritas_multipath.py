from infi.storagemodel.errors import StorageModelFindError, MultipathDaemonTimeoutError, DeviceDisappeared
from infi.storagemodel.unix.utils import execute_command_safe
from infi.storagemodel.base import multipath, gevent_wrapper
from infi.storagemodel.base.disk import NoSuchDisk
from infi.pyutils.lazy import cached_method
from .block import LinuxBlockDeviceMixin
from contextlib import contextmanager
from munch import Munch
import itertools

from logging import getLogger
logger = getLogger(__name__)


class VeritasMultipathEntry(Munch):
    def __init__(self, dmp_name, paths):
        self.paths = paths
        self.dmp_name = dmp_name


class VeritasSinglePathEntry(Munch):
    def __init__(self, sd_device_name, ctlr, state, wwn):
        self.sd_device_name = sd_device_name
        self.ctlr = ctlr
        self.state = state
        self.wwn = wwn


class VeritasMultipathClient(object):
    def get_list_of_multipath_devices(self):
        multipaths = []
        multipath_dicts = self.parse_paths_list(self.read_paths_list())
        for multi in multipath_dicts:
            paths = [VeritasSinglePathEntry(p['name'], p['ctlr'], p['state'], p['aportWWN']) for p in multi['paths']]
            multipaths.append(VeritasMultipathEntry(multi['dmpdev'], paths))
        return multipaths

    def read_paths_list(self):
        return execute_command_safe("vxdmpadm list dmpnode")

    def parse_paths_list(self, paths_list_output):
        from re import compile, MULTILINE, DOTALL
        MULTIPATH_PATTERN = r"^dmpdev\s*=\s*(?P<dmpdev>\w+)\n" + \
                            r"^state\s*=\s*(?P<state>\w+)\n" + \
                            r"^enclosure\s*=\s*(?P<enclosure>\w+)\n" + \
                            r"^cab-sno\s*=\s*(?P<cab_sno>\w+)\n" + \
                            r"^asl\s*=\s*(?P<asl>[\w\.]+)\n" + \
                            r"^vid\s*=\s*(?P<vid>\w+)\n" + \
                            r"^pid\s*=\s*(?P<pid>[\w ]+)\n" + \
                            r"^array-name\s*=\s*(?P<array_name>\w+)\n" + \
                            r"^array-type\s*=\s*(?P<array_type>[\w/]+)\n" + \
                            r"^iopolicy\s*=\s*(?P<iopolicy>\w+)\n" + \
                            r"^avid\s*=\s*(?P<avid>[-\w]+)\n" + \
                            r"^lun-sno\s*=\s*(?P<lun_sno>\w*)\n" + \
                            r"^udid\s*=\s*(?P<udid>[\w%\.-]+)\n" + \
                            r"^dev-attr\s*=\s*(?P<dev_attr>[-\w]+)\n" + \
                            r"^lun_type\s*=\s*(?P<lun_type>[-\w]+)\n" + \
                            r"^scsi3_vpd\s*=\s*(?P<scsi3_vpd>[-\w\:]+)\n" + \
                            r"^replicated\s*=\s*(?P<replicated>\w+)\n" + \
                            r"^num_paths\s*=\s*(?P<num_paths>\w+)\n"  + \
                            r"^###path\s*=[\s\w]+\n" + \
                            r"(?P<paths>(?:^path\s*=\s*[\w -\:\(\)]+\n)*)"
        pattern = compile(MULTIPATH_PATTERN, MULTILINE | DOTALL)
        matches = []
        for match in pattern.finditer(paths_list_output):
            logger.debug("multipath found: %s", match.groupdict())
            multipath_dict = dict((key, value if value is not None else value) \
                              for (key, value) in match.groupdict().items())
            self.parse_paths_in_multipath_dict(multipath_dict)
            matches.append(multipath_dict)
        return matches

    def parse_paths_in_multipath_dict(self, multipath_dict):
        from re import compile, MULTILINE, DOTALL
        PATH_PATTERN = r"^path\s*=\s*" + \
            r"(?P<name>[\w]+)\s*" + \
            r"(?P<state>[\w\(\)]+)\s*" + \
            r"(?P<type>[\w-]+)\s*" + \
            r"(?P<transport>[\w]+)\s*" + \
            r"(?P<ctlr>[\w]+)\s*" + \
            r"(?P<hwpath>[\w]+)\s*" + \
            r"(?P<aportID>[\w-]+)\s*" + \
            r"(?P<aportWWN>[\w:]+)\s*" + \
            r"(?P<attr>[\w-]+)\s*" + \
            r"\n"
        pattern = compile(PATH_PATTERN, MULTILINE | DOTALL)
        matches = []
        for match in pattern.finditer(multipath_dict['paths']):
            logger.debug("paths found: %s", match.groupdict())
            pathgroup_dict = dict((key, value if value is not None else value) for (key, value) in match.groupdict().items())
            matches.append(pathgroup_dict)
        multipath_dict['paths'] = matches


class LinuxVeritasMultipathBlockDevice(multipath.MultipathBlockDevice):
    def __init__(self, sysfs, scsi, multipath_object):
        super(LinuxVeritasMultipathBlockDevice, self).__init__()
        self.multipath_object = multipath_object
        self._sysfs = sysfs
        self._scsi = scsi

    def _is_there_atleast_one_path_up(self):
        return bool(filter(lambda path: path.get_state() == "up", self.get_paths()))

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
    def get_disk_drive(self):  # pragma: no cover
        raise NoSuchDisk

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
