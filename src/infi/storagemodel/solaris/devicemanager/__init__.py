from re import findall
from infi.dtypes.hctl import HCTL
from infi.pyutils.lazy import cached_method
from infi.sgutils.sg_map import get_hctl_for_sd_device

from logging import getLogger
logger = getLogger(__name__)

DISK_DEVICE_PATH = "/dev/dsk"
DISK_RAW_DEVICE_PATH = "/dev/rdsk"
CFG_DEVICE_PATH = "/dev/cfg"
CTRL_DEVICE_PATH = "/dev/scsi/array_ctrl"
DEVICE_MAP_PATH = "/etc/path_to_inst"

class SolarisSCSIDeviceMixin(object):
    @cached_method
    def get_scsi_access_path(self):
        from os import path
        return path.join(self.get_base_dir(), self.get_device_name())

    def get_device_name(self):
        target_string = "t{}".format(self.target) if self.target else ''
        slice_string = "s{}".format(self._slice) if self._slice else ''
        return "c{}{}d{}{}".format(self._controller, target_string, self._disk, slice_string)

    @cached_method
    def get_hctl(self):
        # TODO make sure which is base 16 and which isn't!
        return HCTL(int(self.controller), int(self.controller), int(self.target, 16), int(self.disk))

    #@cached_method TODO - should cache???
    def get_instance_name(self):
        # return device name in a format like sd1,a
        device_path = self.get_full_path()
        device_instance_name = DeviceManager.get_path_to_inst_mapping().get(device_path.split(":")[0], "")
        device_slice = device_path.split(":")[1]
        return "{},{}".format(device_instance_name, device_slice)

    #@cached_method TODO - should cache???
    def get_full_path(self):
        from os import readlink, path
        return path.abspath(path.join(self.get_base_dir(), readlink(path.join(DISK_DEVICE_PATH, self.get_device_name()))))

    @property
    def controller(self):
        return self._controller

    @property
    def target(self):
        return self._target

    @property
    def disk(self):
        return self._disk

    @property
    def base_dir(self):
        raise NotImplementedError


class SolarisBlockDevice(SolarisSCSIDeviceMixin):
    def __init__(self, controller, target, disk, d_slice=''):
        self._controller = controller
        self._target = target
        self._disk = disk
        self._slice = d_slice

    def __str__(self):
        return self.get_device_name()

    def __eq__(self, other):
        return self.get_device_name() == other.get_device_name()

    def get_vendor(self):
        # need to use the kstat library to get this info offline
        raise NotImplemented()

    def get_model(self):
        raise NotImplemented()

    def get_revision(self):
        raise NotImplemented()

    def get_size_in_bytes(self):
        raise NotImplemented()

    def get_base_dir(self):
        return DISK_RAW_DEVICE_PATH


class SolarisStorageController(SolarisSCSIDeviceMixin):
    def __init__(self, controller, target, disk, d_slice=''):
        self._controller = controller
        self._target = target
        self._disk = disk
        self._slice = d_slice

    def get_base_dir(self):
        return CTRL_DEVICE_PATH

    @cached_method
    def get_display_name(self):
        return self.get_device_name()


class DeviceManager(object):
    @classmethod
    def get_ctds_tuple_from_device_name(cls, dev_string):
        try:
            return findall("c([0-9A-F]*)(?:t([0-9A-F]*))?d(\d*)(?:s(\d*))?", dev_string)[0]
        except:
            logger.exception("Can't parse device name: {}".format(dev_string))
            return None

    def get_all_scsi_block_devices(self):
        from os import path, listdir, readlink
        devlist = []
        for device in listdir(DISK_DEVICE_PATH):
            device_fullpath = path.join(DISK_DEVICE_PATH, device)
            if not path.exists(device_fullpath):  # checks the validity of the symlink
                continue
            if not (device.endswith("d0") or device.endswith("s2")):
                continue
            if 'virtual-devices' in readlink(device_fullpath):  # for example, virtual disk in ldom
                continue
            truncated_ctds = DeviceManager.get_ctds_tuple_from_device_name(device.strip("s2"))
            ctds_tuple = DeviceManager.get_ctds_tuple_from_device_name(device)
            if (not ctds_tuple) or len(ctds_tuple[1]) == 32: # filter multipath devices
                continue
            if truncated_ctds and SolarisBlockDevice(*truncated_ctds) not in devlist:
                block_device_obj = SolarisBlockDevice(*ctds_tuple)
                full_path = block_device_obj.get_full_path()
                if 'ide' not in full_path: # filter cdroms
                    devlist.append(block_device_obj)
        return devlist

    def _get_storage_controllers(self, get_multipathed):
        from os import readlink, path, listdir
        def filter_by_link(ctrl):
            if not path.exists(path.join(CTRL_DEVICE_PATH, ctrl)): # checks the validity of the symlink
                return False
            # filter multipathed / non multipathed devices based on the actual device filename
            return get_multipathed ^ ("fp@" in readlink(path.join(CTRL_DEVICE_PATH, ctrl)))
        if path.exists(CTRL_DEVICE_PATH):
            return [SolarisStorageController(*DeviceManager.get_ctds_tuple_from_device_name(ctrl)) \
                for ctrl in listdir(CTRL_DEVICE_PATH) if filter_by_link(ctrl)]
        else:
            return []

    def get_all_scsi_storage_controllers(self):
        return self._get_storage_controllers(get_multipathed=False)

    def get_all_multipathed_storage_controllers(self):
        return self._get_storage_controllers(get_multipathed=True)

    @classmethod
    def _get_path_to_inst_tuples(cls):
        device_map_data = open(DEVICE_MAP_PATH, "rb").read()
        devices = findall("\"(.*)\" (\d*) \"(.*)\"", device_map_data)
        return [(x[0], x[2] + x[1]) for x in devices]

    @classmethod
    def get_path_to_inst_mapping(cls):
        return dict(cls._get_path_to_inst_tuples())

    @classmethod
    def get_inst_to_path_mapping(cls):
        return dict([x[::-1] for x in cls._get_path_to_inst_tuples()])

    @classmethod
    def get_path_to_cfg_mapping(cls):
        from os import readlink, path, listdir
        return {readlink(path.join(CFG_DEVICE_PATH, ctrl)).replace("../../devices", "").split(':')[0] : ctrl \
                for ctrl in listdir(CFG_DEVICE_PATH)}
