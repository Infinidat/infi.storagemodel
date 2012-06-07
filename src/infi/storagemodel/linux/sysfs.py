import os
import glob
from infi.dtypes.hctl import HCTL
from infi.pyutils.lazy import cached_method
from ..errors import DeviceDisappeared

SYSFS_CLASS_SCSI_DEVICE_PATH = "/sys/class/scsi_device"
SYSFS_CLASS_BLOCK_DEVICE_PATH = "/sys/class/block"

SCSI_TYPE_DISK = 0x00
SCSI_TYPE_STORAGE_CONTROLLER = 0x0C

from logging import getLogger
log = getLogger(__name__)

def _sysfs_read_field(device_path, field):
    with open(os.path.join(device_path, field), "rb") as f:
        return f.read()

def _sysfs_read_devno(device_path):
    return tuple([ int(n) for n in _sysfs_read_field(device_path, "dev").strip().split(":") ])

class SysfsBlockDeviceMixin(object):
    def get_block_device_name(self):
        return self.block_device_name

    def get_block_devno(self):
        return _sysfs_read_devno(self.sysfs_block_device_path)

    def get_size_in_bytes(self):
        return int(_sysfs_read_field(self.sysfs_block_device_path, "size")) * 512

class SysfsBlockDevice(SysfsBlockDeviceMixin):
    def __init__(self, block_device_name, block_device_path):
        self.block_device_name = block_device_name
        self.sysfs_block_device_path = block_device_path

    def __repr__(self):
        _repr = "<SysfsBlockDevice(block_device_name={!r}, block_device_path={!r}>"
        return _repr.format(self.block_device_name, self.sysfs_block_device_path)

class SysfsSCSIDevice(object):
    def __init__(self, sysfs_dev_path, hctl):
        super(SysfsSCSIDevice, self).__init__()
        self.sysfs_dev_path = sysfs_dev_path
        self.hctl = hctl
        # on ubuntu: /sys/class/scsi_device/0:0:1:0/device/scsi_generic/sg1
        # on redhat: /sys/class/scsi_device/0:0:1:0/device/scsi_generic:sg1
        basepath = os.path.join(self.sysfs_dev_path, "scsi_generic")
        if os.path.exists(basepath):
            sg_dev_names = os.listdir(basepath)
        else:
            sg_dev_names = glob.glob(os.path.join(self.sysfs_dev_path, "scsi_generic*"))
        if len(sg_dev_names) != 1:
            msg = "{} doesn't have a single device/scsi_generic/sg* path ({!r})"
            raise DeviceDisappeared(msg.format(self.sysfs_dev_path, sg_dev_names))
        self.scsi_generic_device_name = sg_dev_names[0].split(':')[-1]
        self.sysfs_scsi_generic_device_path = os.path.join(self.sysfs_dev_path, "scsi_generic",
                                                           self.scsi_generic_device_name)

    def get_hctl(self):
        return self.hctl

    def get_scsi_generic_device_name(self):
        return self.scsi_generic_device_name

    def get_queue_depth(self):
        return int(_sysfs_read_field(self.sysfs_dev_path, "queue_depth"))

    def get_vendor(self):
        return _sysfs_read_field(self.sysfs_dev_path, "vendor")

    def get_scsi_generic_devno(self):
        return _sysfs_read_devno(self.sysfs_scsi_generic_device_path)

    def __repr__(self):
        _repr = "<SysfsSCSIDevice(sysfs_dev_path={!r}, hctl={!r})>"
        return _repr.format(self.sysfs_dev_path, self.hctl)

    def get_sysfs_dev_path(self):
        return self.sysfs_dev_path

def get_sd_paths(sysfs_dev_path):
    basepath = os.path.join(sysfs_dev_path, "block")
    log.debug("basepath = {!r}".format(basepath))
    if os.path.exists(basepath):
        block_dev_names = os.listdir(basepath)
    else:
        block_dev_names = glob.glob(os.path.join(sysfs_dev_path, "block*"))
    log.debug("block_dev_names = {!r}".format(block_dev_names))
    return block_dev_names

class SysfsSDDisk(SysfsBlockDeviceMixin, SysfsSCSIDevice):
    def __init__(self, sysfs_dev_path, hctl, block_dev_names):
        super(SysfsSDDisk, self).__init__(sysfs_dev_path, hctl)
        # on ubuntu: /sys/class/scsi_device/0:0:1:0/device/block/sdb/
        # on redhat: /sys/class/scsi_device/0:0:1:0/device/block:sdb/
        self.block_device_name = block_dev_names[0].split(':')[-1]
        log.debug("block_device_name = {!r}".format(self.block_device_name))
        self.sysfs_block_device_path = os.path.join(self.sysfs_dev_path, "block", self.block_device_name)
        if not os.path.exists(self.sysfs_block_device_path):
            self.sysfs_block_device_path = os.path.join(self.sysfs_dev_path, "block:{}".format(self.block_device_name))
        log.debug("sysfs_block_device_path = {!r}".format(self.sysfs_block_device_path))

    def __repr__(self):
        _repr = "<SysfsBlockDeviceMixin(sysfs_dev_path={!r}, hctl={!r})>"
        return _repr.format(self.sysfs_dev_path, self.hctl)

class Sysfs(object):
    @cached_method
    def _populate(self):
        for hctl_str in os.listdir(SYSFS_CLASS_SCSI_DEVICE_PATH):
            dev_path = os.path.join(SYSFS_CLASS_SCSI_DEVICE_PATH, hctl_str, "device")
            try:
                scsi_type = int(_sysfs_read_field(dev_path, "type"))
                self._append_device_by_type(hctl_str, dev_path, scsi_type)
            except (IOError, OSError):
                log.debug("no device type for hctl {}".format(hctl_str))

        for name, path in self._get_sysfs_block_devices_pathnames().items():
            dev = SysfsBlockDevice(name, path)
            devno = dev.get_block_devno()
            assert devno not in self.block_devno_to_device
            self.block_devno_to_device[devno] = dev

    def __init__(self):
        self.disks = []
        self.controllers = []
        self.block_devno_to_device = dict()

    def __repr__(self):
        _repr = "<Sysfs: disks={!r}, controllers={!r}, block_devno_to_device={!r}>"
        return _repr.format(self.disks, self.controllers, self.block_devno_to_device)

    def _append_device_by_type(self, hctl_str, dev_path, scsi_type):
        if scsi_type == SCSI_TYPE_STORAGE_CONTROLLER:
            self.controllers.append(SysfsSCSIDevice(dev_path, HCTL.from_string(hctl_str)))
        elif scsi_type == SCSI_TYPE_DISK:
            block_dev_names = get_sd_paths(dev_path)
            if block_dev_names == []:
                self.disks.append(SysfsSCSIDevice(dev_path, HCTL.from_string(hctl_str)))
            else:
                self.disks.append(SysfsSDDisk(dev_path, HCTL.from_string(hctl_str), block_dev_names))

    def _get_sysfs_block_devices_pathnames(self):
        """:returns a dict of name:path"""
        for base in ["/sys/block", ]:
            if os.path.exists(base):
                #  /sys/class/block/sda -> 
                #     ../../devices/pci0000:00/0000:00:15.0/0000:03:00.0/host2/target2:0:0/2:0:0:0/block/sda
                def readlink(src):
                    if os.path.islink(src):
                        return os.path.abspath(os.path.join(base, os.readlink(os.path.join(base, src))))
                    return os.path.join(base, src)
                return {link:readlink(link) for link in os.listdir(base)}

    @cached_method
    def get_all_sd_disks(self):
        self._populate()
        return [disk for disk in self.disks if isinstance(disk, SysfsSDDisk)]

    @cached_method
    def get_all_sg_disks(self):
        self._populate()
        return self.disks

    @cached_method
    def get_all_scsi_storage_controllers(self):
        self._populate()
        return self.controllers

    @cached_method
    def get_all_block_devices(self):
        self._populate()
        return self.block_devices.values()

    def find_block_device_by_devno(self, devno):
        if len(self.block_devno_to_device.keys()) == 0:
            self._populate()
        return self.block_devno_to_device.get(devno, None)

    def find_scsi_disk_by_hctl(self, hctl):
        if len(self.disks) == 0:
            self._populate()
        disk = [ disk for disk in self.disks if disk.get_hctl() == hctl ]
        if len(disk) != 1:
            raise ValueError("cannot find a disk with HCTL %s" % (str(hctl),))
        return disk[0]
