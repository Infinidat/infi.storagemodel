from infi.pyutils.lazy import cached_method
from infi.storagemodel.errors import ScsiGenericNotLoaded
from infi.storagemodel.solaris.devicemanager import DeviceManager
from infi.storagemodel.unix.multipath import UnixPathMixin
from infi.storagemodel.base import multipath, gevent_wrapper
from contextlib import contextmanager
from munch import Munch
from os import path
import re

from logging import getLogger
logger = getLogger(__name__)


class SolarisMultipathEntry(Munch):
    def __init__(self, device_path, vendor_id, product_id, load_balance, paths):
        self.device_path = device_path
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.load_balance = load_balance
        self.paths = paths


class SolarisSinglePathEntry(Munch):
    def __init__(self, initiator_port_name, target_port_name, state, disabled, mpath_dev_path,
                 ports, port_mappings):
        self.initiator_port_name = initiator_port_name
        self.target_port_name = target_port_name
        self.is_iscsi_session = False
        if "iqn." in target_port_name:
            self.is_iscsi_session = True
            self.target_iqn, self.iscsi_session_uid = self._get_target_uid_and_iqn()
        self.state = state
        self.disabled = disabled
        self.ports = ports
        self.port_mappings = port_mappings
        self.mpath_dev_path = mpath_dev_path
        self.hctl = self._get_hctl()

    def _get_target_uid_and_iqn(self):
        '''returns iscsi target iqn and session uid'''
        from infi.dtypes.iqn import IQN
        iqn = self.target_port_name.split(',')[1]
        _ = IQN(iqn)
        uid = self.target_port_name.split(',')[2]
        return iqn, uid

    def _get_path_lun_fc(self):
        for device_name, host_wwn, target_wwn, lun in self.port_mappings:
            if self.mpath_dev_path in device_name.decode() and \
                str(host_wwn) == self.initiator_port_name and \
                str(target_wwn) == self.target_port_name:
                return lun

    def _get_hct_fc(self, hba_port_wwn, remote_port_wwn):
        port_hct = (-1, 0, -1)
        for hba_port in self.ports:
            if not (hba_port.port_wwn == hba_port_wwn):
                continue
            for remote_port in hba_port.discovered_ports:
                if remote_port.port_wwn == remote_port_wwn:
                    port_hct = remote_port.hct
        return port_hct

    def _get_hct_iscsi(self):
        from infi.iscsiapi import get_iscsiapi
        iscsiapi = get_iscsiapi()
        sessions = iscsiapi.get_sessions()
        for session in sessions:
            if session.get_uid() == self.iscsi_session_uid and \
            str(session.get_target().get_iqn()) == self.target_iqn:
                return session.get_hct()
        return (-1, 0, -1)

    def _get_path_lun_iscsi(self):
        from infi.storagemodel.unix.utils import execute_command
        from infi.dtypes.iqn import IQN
        import re
        process = execute_command(['iscsiadm', 'list', 'target', '-S'])
        output = process.get_stdout().splitlines()
        for line_number, line in enumerate(output):
            if re.search(r'Target: ', line):
                result_iqn = line.split()[1]
                _ = IQN(result_iqn)  # make sure iqn is valid
                if result_iqn != self.target_iqn:
                    continue
                for indent_line in range(line_number + 1, len(output)):
                    if re.search(r'TPGT:', output[indent_line]):
                        uid = output[indent_line].split()[1]
                        if uid != self.iscsi_session_uid:
                            break
                    if re.search(r'LUN:', output[indent_line]):
                        lun = output[indent_line].split()[1]
                    if re.search('OS Device Name', output[indent_line]):
                        device_name = output[indent_line].split()[3]
                        if device_name == self.mpath_dev_path:
                            return int(lun)
                        elif "array" in self.mpath_dev_path:
                            if "array" in device_name or "Not" in device_name:
                                msg = "correlating device {} <-> {}, both should be lun 0".format(output[indent_line],
                                                                                                  self.mpath_dev_path)
                                logger.debug(msg)
                                return 0
                        else:
                            continue
                    if re.search(r'Target: ', output[indent_line]):
                        break  # We reached the next target no point searching forward


    def _get_hctl(self):
        from infi.dtypes.hctl import HCTL
        if self.is_iscsi_session:
            h, c, t = self._get_hct_iscsi()
            if (h, c, t) == (-1, 0, -1):
                return None
            else:
                return HCTL(h, c, t, self._get_path_lun_iscsi())
        else:
            h, c, t = self._get_hct_fc(self.initiator_port_name, self.target_port_name)
            if (h, c, t) == (-1, 0, -1):
                return None
            else:
                return HCTL(h, c, t, self._get_path_lun_fc())

    def get_hctl(self):
        return self.hctl


class SolarisMultipathClient(object):
    MULTIPATH_DEVICE_PATTERN = r'(?:/dev/rdsk/|/scsi_vhci/)[\w\@\-]+'
    MULTIPATH_DEVICE_REGEXP = re.compile(MULTIPATH_DEVICE_PATTERN, re.MULTILINE)

    # The regular expression used to "slice" the output of "mpathadm show" - a detailed list of all the multipaths we
    # have on the current host, into logical units, each with its list of paths:
    MPATHADM_OUTPUT_PATTERN = r"\s*(?P<mpath_dev_path>{})\n".format(MULTIPATH_DEVICE_PATTERN) + \
                              r".*?Vendor:\s*(?P<vendor_id>[\w]+)" + \
                              r".*?Product:\s*(?P<product_id>[\w]+)" + \
                              r".*?Current Load Balance:\s*(?P<load_balance>[\w\-]+)" + \
                              r".*?(?:Paths:)?(?P<paths>.*)"
    MPATHADM_OUTPUT_REGEXP = re.compile(MPATHADM_OUTPUT_PATTERN, re.MULTILINE | re.DOTALL)

    PATH_PATTERN = r"^\s*Initiator Port Name:\s*(?P<initiator_port_name>\S+)\s*" + \
                   r"^\s*Target Port Name:\s*(?P<target_port_name>\S+)\s*" + \
                   r"^\s*Override Path:\s*(?P<override_path>\w+)\s*" + \
                   r"^\s*Path State:\s*(?P<state>\w+)\s*" + \
                   r"^\s*Disabled:\s*(?P<disabled>\w+)"
    PATH_REGEXP = re.compile(PATH_PATTERN, re.MULTILINE | re.DOTALL)

    LOGICAL_UNIT_HEADER = 'Logical Unit:'    # Header for each logical unit entry in the output of mpathadm

    def __init__(self):
        from infi.hbaapi import get_ports_generator
        from infi.hbaapi.generators.hbaapi import HbaApi
        self._ports = list(get_ports_generator().iter_ports())
        self._port_mappings = list(HbaApi().iter_port_mappings())

    def get_list_of_multipath_devices(self):
        multipaths = []

        paths_list_output = self.read_multipaths_list()
        logical_units_list = paths_list_output.split(self.LOGICAL_UNIT_HEADER)

        for logical_unit in logical_units_list:
            if not logical_unit:
                continue
            logical_unit_match = self.MPATHADM_OUTPUT_REGEXP.match(logical_unit)
            if not logical_unit_match:
                logger.warn('MPATHADM_OUTPUT_REGEXP did not match logical_unit = {logical_unit}'.format(
                    logical_unit=logical_unit))
                continue
            logical_unit_dict = logical_unit_match.groupdict()

            paths = self.get_paths(logical_unit_dict)

            mpath_dev_path = logical_unit_dict['mpath_dev_path']
            mpath_dev_path = path.join('/devices', mpath_dev_path.lstrip('/')) if \
                'array-controller' in logical_unit_dict['mpath_dev_path'] else mpath_dev_path
            multipaths.append(
                SolarisMultipathEntry(mpath_dev_path,
                                      logical_unit_dict['vendor_id'], logical_unit_dict['product_id'],
                                      logical_unit_dict['load_balance'], paths))
        return multipaths

    def _run_command(self, cmd):
        from infi.execute import ExecutionError
        from infi.storagemodel.unix.utils import execute_command
        try:
            return execute_command(cmd.split()).get_stdout().decode("ascii")
        except OSError as e:
            if e.errno not in (2, 20):  # file not found, not a directory
                logger.exception("{} failed with unknown reason".formart(cmd[0]))
            return ""
        except ExecutionError:
            logger.exception("{} failed, returning empty output".format(cmd[0]))
            return ""

    def read_multipaths_list(self):
        # On Solaris 11, "mpathadm show lu" shows details for all LUNs, so listing them first ("mpathadm list lu") is
        # redundant. On Solaris 10, "mpathadm show lu" expects a LUN operand, therefore we need to list the LUNs first.
        # Listing all LUNs is run-time heavy, we'd like to avoid that if possible:
        from infi.os_info import get_platform_string
        if 'solaris-11' in get_platform_string():
            # For Solaris 11:
            return self._run_command("mpathadm show lu")
        device_list = self._run_command("mpathadm list lu")
        device_paths = self.MULTIPATH_DEVICE_REGEXP.findall(device_list)
        if not device_paths:    # no devices
            logger.debug("no device paths found")
            return ''
        return self._run_command("mpathadm show lu {}".format(" ".join(device_paths)))

    def get_paths(self, logical_unit_dict):
        paths = []
        mpath_dev_path = logical_unit_dict['mpath_dev_path']
        for path_match in self.PATH_REGEXP.finditer(logical_unit_dict['paths']):
            path_dict = path_match.groupdict()
            paths.append(SolarisSinglePathEntry(
                path_dict['initiator_port_name'], path_dict['target_port_name'], path_dict['state'],
                path_dict['disabled'], mpath_dev_path, self._ports, self._port_mappings))
        logger.debug("paths found: %s", paths)
        return paths


class SolarisRoundRobin(multipath.RoundRobin):
    pass


QUERY_TIMEOUT = 3  # 3 seconds

class SolarisNativeMultipathDeviceMixin(object):
    @cached_method
    def get_block_access_path(self):
        return self._multipath_object.device_path

    @cached_method
    def get_paths(self):
        return [SolarisPath(p, self._multipath_object.device_path) for p in self._multipath_object.paths \
                if p.get_hctl() is not None]

    @cached_method
    def get_disk_drive(self):  # pragma: no cover
        raise NotImplementedError

    @cached_method
    def get_display_name(self):
        return self.get_block_access_path().split('/')[-1]

    @cached_method
    def get_policy(self):
        return SolarisRoundRobin()

    def get_scsi_vendor_id(self):
        return self._multipath_object.vendor_id

    def get_scsi_product_id(self):
        return self._multipath_object.product_id


class SolarisNativeMultipathBlockDevice(SolarisNativeMultipathDeviceMixin, multipath.MultipathBlockDevice):
    def __init__(self, multipath_object):
        super(SolarisNativeMultipathBlockDevice, self).__init__()
        self._multipath_object = multipath_object

    @contextmanager
    def asi_context(self):
        import os
        from infi.asi import create_platform_command_executer, create_os_file

        handle = create_os_file(self.get_block_access_path())
        executer = create_platform_command_executer(handle, timeout=QUERY_TIMEOUT)
        executer.call = gevent_wrapper.defer(executer.call)
        try:
            yield executer
        finally:
            handle.close()


class SolarisNativeMultipathStorageController(SolarisNativeMultipathDeviceMixin, multipath.MultipathStorageController):
    def __init__(self, multipath_object):
        super(SolarisNativeMultipathStorageController, self).__init__()
        self._multipath_object = multipath_object

    @cached_method
    def get_multipath_access_path(self):
        return self.get_block_access_path()

    @cached_method
    def get_block_access_path(self):
        return self._multipath_object.device_path + ":array_ctrl"

    @contextmanager
    def asi_context(self):
        import os
        from infi.asi import create_platform_command_executer, create_os_file

        # if sgen is not loaded we can't open the device
        if not os.path.exists(self.get_block_access_path()) and os.path.exists(self.get_block_access_path().strip(":array_ctrl")):
            msg = "can't query device {} since block access path doesn't exist (sgen is not loaded)".format(self.get_display_name())
            raise ScsiGenericNotLoaded(msg)

        handle = create_os_file(self.get_block_access_path())
        executer = create_platform_command_executer(handle, timeout=QUERY_TIMEOUT)
        executer.call = gevent_wrapper.defer(executer.call)
        try:
            yield executer
        finally:
            handle.close()


class SolarisPath(UnixPathMixin, multipath.Path):
    def __init__(self, multipath_object_path, device_path):
        self.multipath_object_path = multipath_object_path
        self.device_path = device_path

    @cached_method
    def get_path_id(self):
        hctl = self.get_hctl()
        return "c{host_id}::{target_wwn},{lun}".format(host_id=hctl.get_host(), target_wwn=self.multipath_object_path.target_port_name, lun=hctl.get_lun())

    def get_hctl(self):
        return self.multipath_object_path.get_hctl()

    @cached_method
    def get_state(self):
        return "up" if ("OK" in self.multipath_object_path.state and "no" in self.multipath_object_path.disabled) else "down"

    def get_io_statistics(self):
        from infi.storagemodel.solaris.devicemanager.kstat import KStat
        from os import readlink
        all_stats = KStat().get_io_stats()
        full_dev_path = '/scsi_vhci/' + readlink(self.device_path).split('/')[-1].split(':')[0]
        stats = all_stats[full_dev_path]['c{}'.format(self.get_hctl().get_host())][self.multipath_object_path.target_port_name]
        return multipath.PathStatistics(stats.bytes_read, stats.bytes_written, stats.read_io_count, stats.write_io_count)

    @contextmanager
    def asi_context(self):
        import os
        from infi.asi import create_platform_command_executer, create_os_file

        handle = create_os_file(self.device_path)
        executer = create_platform_command_executer(handle, timeout=QUERY_TIMEOUT)
        executer.call = gevent_wrapper.defer(executer.call)
        try:
            yield executer
        finally:
            handle.close()


class SolarisNativeMultipathModel(multipath.NativeMultipathModel):
    def __init__(self, *args, **kwargs):
        super(SolarisNativeMultipathModel, self).__init__(*args, **kwargs)
        self._device_manager = DeviceManager()

    def _is_device_active(self, multipath_device):
        return any('OK' in path.state and 'no' in path.disabled for path in multipath_device.paths)

    @cached_method
    def _get_list_of_active_devices(self, client):
        all_devices = client.get_list_of_multipath_devices()
        logger.debug("all multipath devices = {}".format(all_devices))
        active_devices = [device for device in all_devices if self._is_device_active(device)]
        return active_devices

    @cached_method
    def get_all_multipath_block_devices(self):
        client = SolarisMultipathClient()
        devices = self._get_list_of_active_devices(client)
        result = [SolarisNativeMultipathBlockDevice(d) for d in devices if 'array-controller' not in d.device_path]
        msg = "Got {}  block devices from multipath client (out of {} total)"
        logger.debug(msg.format(len(result), len(devices)))
        return result

    @cached_method
    def get_all_multipath_storage_controller_devices(self):
        # TODO get actual device path from device manager
        client = SolarisMultipathClient()
        devices = self._get_list_of_active_devices(client)
        result = [SolarisNativeMultipathStorageController(d) for d in devices if 'array-controller' in d.device_path]
        msg = "Got {} storage controller devices from multipath client (out of {} total)"
        logger.debug(msg.format(len(result), len(devices)))
        return result

    def filter_non_multipath_scsi_block_devices(self, scsi_block_devices):
        """Returns items from the list that are not part of multipath devices claimed by this framework"""
        return scsi_block_devices  # no co-existence

    def filter_non_multipath_scsi_storage_controller_devices(self, scsi_controller_devices):
        """Returns items from the list that are not part of multipath devices claimed by this framework"""
        return scsi_controller_devices  # no co-existence
