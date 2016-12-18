import os
import glob
from infi.dtypes.hctl import HCTL
from infi.pyutils.lazy import cached_method
from ..errors import DeviceError
from infi.sgutils.sg_map import get_hctl_for_sd_device

SYSFS_CLASS_SCSI_DEVICE_PATH = "/sys/class/scsi_device"
SYSFS_CLASS_BLOCK_DEVICE_PATH = "/sys/class/block"
SYSFS_CLASS_ENCLOSURE_DEVICE_PATH = "/sys/class/enclosure"
SYSFS_CLASS_ALL_DEVICE_PATH = "/dev"

SCSI_TYPE_DISK = 0x00
SCSI_TYPE_STORAGE_CONTROLLER = 0x0C
SCSI_TYPE_ENCLOSURE = 0x0D


from logging import getLogger
log = getLogger(__name__)


def _sysfs_read_field(device_path, field):
    with open(os.path.join(device_path, field), "r") as f:
        return f.read()


def _sysfs_read_devno(device_path):
    return tuple([int(n) for n in _sysfs_read_field(device_path, "dev").strip().split(":")])


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
        _repr = "<{}(block_device_name={!r}, block_device_path={!r}>"
        return _repr.format(self.__class__.__name__, self.block_device_name, self.sysfs_block_device_path)


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
            raise DeviceError(msg.format(self.sysfs_dev_path, sg_dev_names))
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

    def get_model(self):
        return _sysfs_read_field(self.sysfs_dev_path, "model")

    def get_revision(self):
        return _sysfs_read_field(self.sysfs_dev_path, "rev")

    def get_sas_address(self):
        if os.path.exists(os.path.join(self.sysfs_dev_path, "sas_address")):
            return _sysfs_read_field(self.sysfs_dev_path, "sas_address").strip()
        else:
            return None

    def get_scsi_generic_devno(self):
        return _sysfs_read_devno(self.sysfs_scsi_generic_device_path)

    def __repr__(self):
        _repr = "<{}(sysfs_dev_path={!r}, hctl={!r})>"
        return _repr.format(self.__class__.__name__, self.sysfs_dev_path, self.hctl)

    def get_sysfs_dev_path(self):
        return self.sysfs_dev_path


class SysfsSDDisk(SysfsBlockDeviceMixin, SysfsSCSIDevice):
    def __init__(self, sysfs_dev_path, hctl, block_dev_names):
        super(SysfsSDDisk, self).__init__(sysfs_dev_path, hctl)
        # on ubuntu: /sys/class/scsi_device/0:0:1:0/device/block/sdb/
        # on redhat: /sys/class/scsi_device/0:0:1:0/device/block:sdb/
        self.block_device_name = block_dev_names[0].split(':')[-1]
        log.debug("block_device_name = {!r}".format(self.block_device_name))
        self.sysfs_block_device_path = os.path.join(os.path.sep, 'sys', 'block', self.block_device_name)
        log.debug("sysfs_block_device_path = {!r}".format(self.sysfs_block_device_path))

    def __repr__(self):
        _repr = "<{}(sysfs_dev_path={!r}, hctl={!r})>"
        return _repr.format(self.__class__.__name__, self.sysfs_dev_path, self.hctl)


class SysfsEnclosureDevice(SysfsSCSIDevice):
    def __init__(self, sysfs_dev_path, hctl):
        super(SysfsEnclosureDevice, self).__init__(sysfs_dev_path, hctl)
        # /sys/class/scsi_device/h:c:t:l/device/enclosure/h:c:t:l
        self._basepath = os.path.join(self.sysfs_dev_path, 'enclosure', str(hctl))

    @cached_method
    def get_all_slots(self):
        slots = []
        for item in os.listdir(self._basepath):
            if item.startswith('SLOT'):
                slots.append(item)
        return slots

    def get_all_occupied_slots(self):
        occupied_slots = []
        for slot in self.get_all_slots():
            status = _sysfs_read_field(os.path.join(self._basepath, slot), "status")
            if status == 'OK':
                occupied_slots.append(slot)
        return occupied_slots

    def find_hctl_by_slot(self, slot):
        dev_path = os.path.join(self._basepath, slot, 'device')
        if os.path.exists(dev_path):
            hctl = os.path.basename(os.readlink(dev_path))
            return HCTL.from_string(hctl)
        return None


class Sysfs(object):
    def __init__(self):
        self.sg_disks = []
        self.sd_disks = []
        self.controllers = []
        self.enclosures = []
        self.block_devices = []
        self.block_devno_to_device = dict()

    @cached_method
    def _populate(self):
        self._sd_structures = {} # hctl_str : list of device paths

        for d in os.listdir(SYSFS_CLASS_ALL_DEVICE_PATH):
            # listdir returns /dev/sda and /dev/sda1
            if not d.startswith("sd") or d[-1].isdigit():
                continue

            dev_path = os.path.join(SYSFS_CLASS_ALL_DEVICE_PATH, d)
            try:
                hctl = get_hctl_for_sd_device(dev_path)
            except (IOError, OSError):
                log.debug("no hctl for sd device {}".format(dev_path))
                continue
            self._sd_structures.setdefault(hctl, []).append(d)

        for hctl_str in os.listdir(SYSFS_CLASS_SCSI_DEVICE_PATH):
            dev_path = os.path.join(SYSFS_CLASS_SCSI_DEVICE_PATH, hctl_str, "device")
            try:
                scsi_type = int(_sysfs_read_field(dev_path, "type"))
                self._append_device_by_type(hctl_str, dev_path, scsi_type)
            except (IOError, OSError):
                log.debug("no device type for hctl {}".format(hctl_str))
            except (DeviceError):
                log.debug("device for hctl {} is dangling, skipping it".format(hctl_str))

        for name, path in self._get_sysfs_block_devices_pathnames().items():
            dev = SysfsBlockDevice(name, path)
            try:
                devno = dev.get_block_devno()
                if devno not in self.block_devno_to_device:
                    self.block_devno_to_device[devno] = dev
                    self.block_devices.append(dev)
            except (IOError, OSError):
                log.debug("no device for {}".format(dev))

    def _append_device_by_type(self, hctl_str, dev_path, scsi_type):
        if scsi_type == SCSI_TYPE_STORAGE_CONTROLLER:
            self.controllers.append(SysfsSCSIDevice(dev_path, HCTL.from_string(hctl_str)))
        elif scsi_type == SCSI_TYPE_ENCLOSURE:
            self.enclosures.append(SysfsEnclosureDevice(dev_path, HCTL.from_string(hctl_str)))
        elif scsi_type == SCSI_TYPE_DISK:
            block_dev_names = self._sd_structures.get(hctl_str)
            if not block_dev_names:
                self.sg_disks.append(SysfsSCSIDevice(dev_path, HCTL.from_string(hctl_str)))
            else:
                sd_disk = SysfsSDDisk(dev_path, HCTL.from_string(hctl_str), block_dev_names)
                self.sd_disks.append(sd_disk)
                self.sg_disks.append(sd_disk)
                self.block_devices.append(sd_disk)
                self.block_devno_to_device[sd_disk.get_block_devno()] = sd_disk

    def _get_sysfs_block_devices_pathnames(self):
        """ Returns a dict of name:path """
        for base in ["/sys/block", ]:
            if os.path.exists(base):
                #  /sys/class/block/sda ->
                #     ../../devices/pci0000:00/0000:00:15.0/0000:03:00.0/host2/target2:0:0/2:0:0:0/block/sda
                def readlink(src):
                    if os.path.islink(src):
                        try:
                            return os.path.abspath(os.path.join(base, os.readlink(os.path.join(base, src))))
                        except (OSError, IOError):
                            return os.path.join(base, src)
                    return os.path.join(base, src)
                return {link: readlink(link) for link in os.listdir(base)}

    @cached_method
    def get_all_sd_disks(self):
        self._populate()
        return self.sd_disks

    @cached_method
    def get_all_sg_disks(self):
        self._populate()
        return self.sg_disks

    @cached_method
    def get_all_scsi_storage_controllers(self):
        self._populate()
        return self.controllers

    @cached_method
    def get_all_enclosures(self):
        self._populate()
        return self.enclosures

    @cached_method
    def get_all_block_devices(self):
        self._populate()
        return self.block_devices

    def find_block_device_by_devno(self, devno):
        self._populate()
        return self.block_devno_to_device.get(devno, None)

    def find_scsi_disk_by_hctl(self, hctl):
        self._populate()
        disk = [disk for disk in self.sd_disks if disk.get_hctl() == hctl]
        if len(disk) != 1:
            raise ValueError("cannot find a disk with HCTL %s" % (str(hctl),))
        return disk[0]

    def __repr__(self):
        _repr = ("<{}: sg_disks={!r}, sd_disks={!r}, controllers={!r}, block_devices={!r}, " +
                 "block_devno_to_device={!r}, enclosures={!r}>")
        return _repr.format(self.__class__.__name__, self.sg_disks, self.sd_disks, self.controllers,
                            self.block_devices, self.block_devno_to_device, self.enclosures)
