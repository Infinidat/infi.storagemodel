from logging import getLogger
from os import path, getpid
try:
    from os import readlink
except ImportError: # windows
    readlink = None
from re import search
from glob import glob
from .utils import func_logger

logger = getLogger(__name__)

PROC_SCSI_SCSI_LINE_TEMPLATE = "Host: scsi{} Channel: {:02d} Id: {:02d} Lun: {:02d}"

@func_logger
def get_scsi_device_names_from_sysfs():
    base = "/sys/class/scsi_device/*"
    return [path.basename(item) for item in glob(base)]

@func_logger
def get_proc_scsi_scsi():
    with open("/proc/scsi/scsi") as fd:
        return fd.read()


def should_scan_scsi_host(dirpath):
    try:
        dst = readlink(dirpath)
    except:
        return True
    if path.sep + 'ata' in dst:
        return False
    return True


@func_logger
def get_hosts():
    return [int(search(r"host(\d+)", dirpath).group(1)) for
            dirpath in glob("/sys/class/scsi_host/host*") if
            should_scan_scsi_host(dirpath)]

@func_logger
def get_channels(host):
    matching_host = [item for item in get_scsi_device_names_from_sysfs()
                     if item.startswith("{}:".format(host))]
    channels = set([int(device.split(":")[1])
                    for device in matching_host])
    return channels

@func_logger
def get_targets(host, channel):
    matching_host_and_channel = [item for item in get_scsi_device_names_from_sysfs()
                                 if item.startswith("{}:{}:".format(host, channel))]
    targets = set([int(device.split(":")[2])
                    for device in matching_host_and_channel])
    return targets

@func_logger
def get_luns(host, channel, target):
    matching_host_channel_and_target = [item for item in get_scsi_device_names_from_sysfs()
                                        if item.startswith("{}:{}:{}:".format(host, channel, target))]
    luns = set([int(device.split(":")[3])
                for device in matching_host_channel_and_target])
    return luns

@func_logger
def is_hctl_written_in_proc_scsi_scsi(host, channel, target, lun):
    expression = PROC_SCSI_SCSI_LINE_TEMPLATE.format(host, channel, target, lun)
    return expression in get_proc_scsi_scsi()

@func_logger
def is_device_exist(host, channel, target, lun):
    return is_hctl_written_in_proc_scsi_scsi(host, channel, target, lun)

@func_logger
def try_readlink(src):
    from os import readlink
    try:
        return readlink(src)
    except OSError as err:
        logger.error("{} OSError {} when readlink {}".format(getpid(), err, src))
        return '/dev/null'

@func_logger
def get_scsi_generic_device(host, channel, target, lun):
    from os import readlink
    hctl = "{}:{}:{}:{}".format(host, channel, target, lun)
    guess = "/sys/class/scsi_device/{}/device/generic".format(hctl)
    if path.exists(guess):
        return path.basename(readlink(guess))
    [sg_x] = [path.basename(sg_x) for sg_x in glob("/sys/class/scsi_generic/sg*")
             if hctl in try_readlink(sg_x)] or [None]
    return sg_x

def is_there_a_bug_in_target_removal():
    from platform import linux_distribution
    # In this case, the target was removed and the SCSI mid-layer will delete the devices
    # once the FC driver deletes the remote port
    # There is a sublte race in the Ubuntu kernel so we don't remove the devices manually
    distname, _, _ = linux_distribution()
    return distname in ["Ubuntu"]

def is_there_a_bug_in_sysfs_async_scanning():
    from platform import linux_distribution
    # http://lkml.indiana.edu/hypermail/linux/kernel/0704.2/1108.html
    distname, version, _ = linux_distribution()
    return distname.lower().split()[0] in ['red', 'redhat', 'centos'] and (version.startswith('5') or version.startswith('6'))

def is_sg_module_loaded():
    with open('/proc/modules') as fd:
        return 'sg ' in fd.read()  # sg 40721 0 - Live 0xffffffffa034f000
