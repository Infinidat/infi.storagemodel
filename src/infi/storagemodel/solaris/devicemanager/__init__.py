from re import findall
from infi.sgutils.sg_map import get_hctl_for_sd_device
from infi.pyutils.lazy import cached_method

from logging import getLogger
logger = getLogger(__name__)

DISK_DEVICE_PATH = "/dev/dsk"
DISK_RAW_DEVICE_PATH = "/dev/rdsk"
MULTIPATH_DEVICE_PATH = "/dev/scsi/array_ctrl"
DEVICE_MAP_PATH = "/etc/path_to_inst"

class SolarisBlockDevice(object):
    def __init__(self, controller, target, disk, d_slice=''):
        self._controller = controller
        self._target = target
        self._disk = disk
        self._slice = d_slice

    def _get_device_map(self):
        device_map_data = open(DEVICE_MAP_PATH, "rb").read()
        devices = findall("\"(.*)\" (\d*) \"(.*)\"", device_map_data)
        device_map = {}
        for device in devices:
            device_map[device[0]] = "{}{}".format(device[2], device[1])
        return device_map

    def get_controller(self):
        return self._controller

    def get_target(self):
        return self._target

    def get_disk(self):
        return self._disk

    def get_device_name(self):
        slice_string = "s{}".format(self._slice) if not self._slice == '' else ''
        return "c{}t{}d{}{}".format(self._controller, self._target, self._disk, slice_string)

    @cached_method
    def get_sd_name(self):
        # return device name in a format like sd1,a
        from os import readlink, path
        device_path = readlink(path.join(DISK_DEVICE_PATH, self.get_device_name())).replace("../../devices", "")
        device_sd_name = self._get_device_map()[device_path.split(":")[0]]
        device_slice = device_path.split(":")[1]
        return "{},{}".format(device_sd_name, device_slice)

    def __str__(self):
        return self.get_device_name()

    def get_raw_device_path(self):
        from os.path import join
        return join(DISK_RAW_DEVICE_PATH, self.get_device_name())

    def get_device_path(self):
        from os.path import join
        return join(DISK_DEVICE_PATH, self.get_device_name())

    def get_vendor(self):
        # need to use the kstat library to get this info offline
        raise NotImplemented()

    def get_model(self):
        raise NotImplemented()

    def get_revision(self):
        raise NotImplemented()

    def get_size_in_bytes(self):
        raise NotImplemented()

class DeviceManager(object):
    def __init__(self):
        device_list = []

    def _get_device_object(self, dev_string):
        try:
            device_info = findall("c(.*)t(.*)d(\d*)(?:s(\d*))?", dev_string)[0]
            return SolarisBlockDevice(*device_info)
        except:
            logger.exception("Can't parse device name: {}".format(dev_string))
            return None

    def get_all_devices(self):
        devlist = []
        from os import listdir
        from os.path import exists, join
        for device in listdir(DISK_DEVICE_PATH):
            if not exists(join(DISK_DEVICE_PATH, device)):
                continue
            if device.endswith("d0"):
                devlist.append(device)
            elif device.endswith("s2") and device[:-2] not in devlist:
                devlist.append(device)
        return [self._get_device_object(device) for device in devlist]
