from infi.pyutils.lazy import cached_method
from infi.storagemodel.errors import ScsiGenericNotLoaded
from infi.storagemodel.solaris.devicemanager import DeviceManager
from infi.storagemodel.base import multipath, gevent_wrapper
from contextlib import contextmanager
from munch import Munch
from os import path

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
    def __init__(self, initiator_port_name, target_port_name, state, disabled, mpath_dev_path, ports):
        self.initiator_port_name = initiator_port_name
        self.target_port_name = target_port_name
        self.is_iscsi_session = False
        if "iqn." in target_port_name:
            self.is_iscsi_session = True
            self.target_iqn, self.iscsi_session_uid = self._get_target_uid_and_iqn()
        self.state = state
        self.disabled = disabled
        self.ports = ports
        self.mpath_dev_path = mpath_dev_path
        self.hctl = self._get_hctl(mpath_dev_path)

    def _get_target_uid_and_iqn(self):
        '''returns iscsi target iqn and session uid'''
        from infi.dtypes.iqn import IQN
        iqn = self.target_port_name.split(',')[1]
        _ = IQN(iqn)
        uid = self.target_port_name.split(',')[2]
        return iqn, uid

    def _get_path_lun_fc(self):
        from infi.hbaapi.generators.hbaapi import HbaApi
        for device_name, host_wwn, target_wwn, lun in HbaApi().iter_port_mappings():
            if self.mpath_dev_path in device_name and \
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


    def _get_hctl(self, mpath_dev_path):
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
    def get_list_of_multipath_devices(self):
        from infi.hbaapi import get_ports_generator
        ports = list(get_ports_generator().iter_ports())

        multipaths = []
        multipath_device_paths = self.parse_paths_list(self.read_multipaths_list())
        for mpath_dev_path in multipath_device_paths:
            info = self.parse_single_paths_list(mpath_dev_path, self.read_single_paths_list(mpath_dev_path))
            if info is None:
                continue
            vendor_id, product_id, load_balance = info['vendor_id'], info['product_id'], info['load_balance']
            paths = [SolarisSinglePathEntry(p['initiator_port_name'], p['target_port_name'], p['state'],
                                            p['disabled'], mpath_dev_path, ports) for p in info['paths']]
            mpath_dev_path = path.join('/devices', mpath_dev_path.lstrip('/')) if \
                'array-controller' in mpath_dev_path else mpath_dev_path
            multipaths.append(SolarisMultipathEntry(mpath_dev_path, vendor_id, product_id, load_balance, paths))
        return multipaths

    def _run_command(self, cmd):
        from infi.execute import ExecutionError
        from infi.storagemodel.unix.utils import execute_command
        try:
            return execute_command(cmd.split()).get_stdout()
        except OSError as e:
            if e.errno not in (2, 20):  # file not found, not a directory
                logger.exception("{} failed with unknown reason".formart(cmd[0]))
            return ""
        except ExecutionError:
            logger.exception("{} failed, returning empty output".format(cmd[0]))
            return ""

    def read_multipaths_list(self):
        return self._run_command("mpathadm list lu")

    def read_single_paths_list(self, device):
        return self._run_command("mpathadm show lu {}".format(device))

    def parse_paths_list(self, paths_list_output):
        from re import compile, MULTILINE, DOTALL
        MULTIPATH_PATTERN = r"^\s*(?P<device_path>(?:/dev/rdsk/|/scsi_vhci/)[\w\@\-]+)\s+Total Path Count:\s*[0-9]+\s*Operational Path Count:\s*[0-9]+\s*$"
        pattern = compile(MULTIPATH_PATTERN, MULTILINE | DOTALL)
        return pattern.findall(paths_list_output)

    def parse_single_paths_list(self, mpath_dev_path, paths_list_output):
        from re import compile, MULTILINE, DOTALL
        def get_extra_info():
            EXTRA_INFO_PATTERN = r"\s*Logical Unit:\s*{}".format(mpath_dev_path) + \
                                 r".*Vendor:\s*(?P<vendor_id>[\w]+)" + \
                                 r".*Product:\s*(?P<product_id>[\w]+)" + \
                                 r".*Current Load Balance:\s*(?P<load_balance>[\w\-]+)"
            res = list(compile(EXTRA_INFO_PATTERN, MULTILINE | DOTALL).finditer(paths_list_output))
            return res[0].groupdict() if res else None
        def get_paths():
            PATH_PATTERN = r"^\s*Initiator Port Name:\s*(?P<initiator_port_name>\S+)\s*" + \
                           r"^\s*Target Port Name:\s*(?P<target_port_name>\S+)\s*" + \
                           r"^\s*Override Path:\s*(?P<override_path>\w+)\s*" + \
                           r"^\s*Path State:\s*(?P<state>\w+)\s*" + \
                           r"^\s*Disabled:\s*(?P<disabled>\w+)\s*$"
            pattern = compile(PATH_PATTERN, MULTILINE | DOTALL)
            matches = [m.groupdict() for m in pattern.finditer(paths_list_output)]
            logger.debug("paths found: %s", matches)
            return matches
        info = get_extra_info()
        if info is not None:
            info['paths'] = get_paths()
        return info


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


class SolarisPath(multipath.Path):
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


class SolarisNativeMultipathModel(multipath.NativeMultipathModel):
    def __init__(self, *args, **kwargs):
        super(SolarisNativeMultipathModel, self).__init__(*args, **kwargs)
        self._device_manager = DeviceManager()

    def _is_device_active(self, multipath_device):
        return any('OK' in path.state and 'no' in path.disabled for path in multipath_device.paths)

    def _get_list_of_active_devices(self, client):
        all_devices = client.get_list_of_multipath_devices()
        logger.debug("all multipath devices = {}".format(all_devices))
        active_devices = [device for device in all_devices if self._is_device_active(device)]
        return active_devices

    @cached_method
    def get_all_multipath_block_devices(self):
        client = SolarisMultipathClient()
        devices = self._get_list_of_active_devices(client)
        logger.debug("Got {} block devices from multipath client".format(len(devices)))
        return [SolarisNativeMultipathBlockDevice(d) for d in devices if 'array-controller' not in d.device_path]

    @cached_method
    def get_all_multipath_storage_controller_devices(self):
        # TODO get actual device path from device manager
        client = SolarisMultipathClient()
        devices = self._get_list_of_active_devices(client)
        logger.debug("Got {} storage controller devices from multipath client".format(len(devices)))
        return [SolarisNativeMultipathStorageController(d) for d in devices if 'array-controller' in d.device_path]

    def filter_non_multipath_scsi_block_devices(self, scsi_block_devices):
        """Returns items from the list that are not part of multipath devices claimed by this framework"""
        return scsi_block_devices  # no co-existence

    def filter_non_multipath_scsi_storage_controller_devices(self, scsi_controller_devices):
        """Returns items from the list that are not part of multipath devices claimed by this framework"""
        return scsi_controller_devices  # no co-existence
