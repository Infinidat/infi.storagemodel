from infi.storagemodel.unix.veritas_multipath import VeritasMultipathClient
from infi.storagemodel.base import multipath, gevent_wrapper
from infi.pyutils.lazy import cached_method
from contextlib import contextmanager
import os

from logging import getLogger
logger = getLogger(__name__)


QUERY_TIMEOUT = 3 # 3 seconds

class SolarisVeritasMultipathBlockDevice(multipath.MultipathBlockDevice):
    def __init__(self, scsi, multipath_object):
        super(SolarisVeritasMultipathBlockDevice, self).__init__()
        self.multipath_object = multipath_object
        self._scsi = scsi

    def _is_there_atleast_one_path_up(self):
        return any(path.get_state() == "up" for path in self.get_paths())

    @cached_method
    def get_display_name(self):
        return self.multipath_object.dmp_name

    @cached_method
    def get_block_access_path(self):
        return "/dev/vx/rdmp/{}".format(self.multipath_object.dmp_name)

    @cached_method
    def get_paths(self):
        paths = list()
        for path in self.multipath_object.paths:
            try:
                paths.append(VeritasPath(self._scsi, path))
            except (ValueError, KeyError):
                logger.debug("VeritasPath device disappeared for {}".format(path))
        return paths

    @cached_method
    def get_policy(self):
        raise NotImplementedError() # TODO

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

    @cached_method
    def get_disk_drive(self):  # pragma: no cover
        raise NotImplementedError

    def get_scsi_vendor_id(self):
        return self.multipath_object.vendor_id

    def get_scsi_product_id(self):
        return self.multipath_object.product_id


class VeritasPath(multipath.Path):
    def __init__(self, scsi_model, multipath_object_path):
        self._scsi_model = scsi_model
        self.multipath_object_path = multipath_object_path
        self.block_access_path = '/dev/rdsk/{}'.format(self.multipath_object_path.sd_device_name)
        self.hctl = self._scsi_model.find_scsi_block_device_by_block_access_path(self.block_access_path).get_hctl()

    @cached_method
    def get_path_id(self):
        return self.multipath_object_path.sd_device_name

    def get_hctl(self):
        return self.hctl

    @cached_method
    def get_state(self):
        return "up" if "enabled" in self.multipath_object_path.state else "down"

    def get_io_statistics(self):
        # TODO we can relate between os names and veritas names using vxdisk -e list and get the stats using kstat
        return multipath.PathStatistics(-1, -1, -1, -1)


class SolarisVeritasMultipathModel(multipath.VeritasMultipathModel):
    def __init__(self, scsi):
        super(SolarisVeritasMultipathModel, self).__init__()
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
        result = [SolarisVeritasMultipathBlockDevice(self._scsi, d) for d in devices]
        return [d for d in result if d._is_there_atleast_one_path_up()]

    @cached_method
    def get_all_multipath_storage_controller_devices(self):
        return []
