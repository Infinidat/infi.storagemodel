from logging import getLogger
from os import path, readlink, getpid
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
    try:
        return readlink(src)
    except OSError, err:
        logger.error("{} OSError {} when readlink {}".format(getpid(), err, src))
        return '/dev/null'

@func_logger
def get_scsi_generic_device(host, channel, target, lun):
    hctl = "{}:{}:{}:{}".format(host, channel, target, lun)
    guess = "/sys/class/scsi_device/{}/device/generic".format(hctl)
    if path.exists(guess):
        return path.basename(readlink(guess))
    [sg_x] = [path.basename(sg_x) for sg_x in glob("/sys/class/scsi_generic/sg*")
             if hctl in try_readlink(sg_x)] or [None]
    return sg_x
