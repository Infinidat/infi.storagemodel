import os
import glob
from infi.dtypes.hctl import HCTL
from ..errors import StorageModelError

SYSFS_CLASS_SCSI_DEVICE_PATH = "/sys/class/scsi_device"
SYSFS_CLASS_BLOCK_DEVICE_PATH = "/sys/class/block"

SCSI_TYPE_DISK = 0x00
SCSI_TYPE_STORAGE_CONTROLLER = 0x0C

class SysfsError(StorageModelError):
    pass

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
            raise SysfsError(msg.format(self.sysfs_dev_path, sg_dev_names))
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

class SysfsSCSIDisk(SysfsBlockDeviceMixin, SysfsSCSIDevice):
    def __init__(self, sysfs_dev_path, hctl):
        super(SysfsSCSIDisk, self).__init__(sysfs_dev_path, hctl)

        # on ubuntu: /sys/class/scsi_device/0:0:1:0/device/block/sdb/
        # on redhat: /sys/class/scsi_device/0:0:1:0/device/block:sdb/

        basepath = os.path.join(self.sysfs_dev_path, "block")
        if os.path.exists(basepath):
            block_dev_names = os.listdir(basepath)
        else:
            block_dev_names = glob.glob(os.path.join(self.sysfs_dev_path, "block*"))
        if len(block_dev_names) != 1:
            msg = "{} doesn't have a single device/lbock/sg* path ({!r})"
            raise SysfsError(msg.format(self.sysfs_dev_path, block_dev_names))
        self.block_device_name = block_dev_names[0].split(':')[-1]
        self.sysfs_block_device_path = os.path.join(self.sysfs_dev_path, "block", self.block_device_name)

class Sysfs(object):
    def __init__(self):
        self.disks = []
        self.controllers = []
        self.block_devno_to_device = dict()

        for hctl_str in os.listdir(SYSFS_CLASS_SCSI_DEVICE_PATH):
            dev_path = os.path.join(SYSFS_CLASS_SCSI_DEVICE_PATH, hctl_str, "device")
            scsi_type = int(_sysfs_read_field(dev_path, "type"))
            if scsi_type == SCSI_TYPE_STORAGE_CONTROLLER:
                self.controllers.append(SysfsSCSIDevice(dev_path, HCTL.from_string(hctl_str)))
            elif scsi_type == SCSI_TYPE_DISK:
                self.disks.append(SysfsSCSIDisk(dev_path, HCTL.from_string(hctl_str)))

        for name, path in self._get_sysfs_block_devices_pathnames().items():
            dev = SysfsBlockDevice(name, path)
            devno = dev.get_block_devno()
            assert devno not in self.block_devno_to_device
            self.block_devno_to_device[devno] = dev

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

    def get_all_scsi_disks(self):
        return self.disks

    def get_all_scsi_storage_controllers(self):
        return self.controllers

    def get_all_block_devices(self):
        return self.block_devices.values()

    def find_block_device_by_devno(self, devno):
        return self.block_devno_to_device.get(devno, None)

    def find_scsi_disk_by_hctl(self, hctl):
        disk = [ disk for disk in self.disks if disk.get_hctl() == hctl ]
        if len(disk) != 1:
            raise ValueError("cannot find a disk with HCTL %s" % (str(hctl),))
        return disk[0]
