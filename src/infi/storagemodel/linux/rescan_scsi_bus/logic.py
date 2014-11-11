from os import getpid
from logging import getLogger
from .utils import func_logger, format_hctl, ScsiCommandFailed
from .scsi import scsi_host_scan, scsi_add_single_device, remove_device_via_sysfs
from .scsi import do_report_luns, do_standard_inquiry, do_test_unit_ready
from .getters import get_scsi_generic_device
from .getters import get_hosts, get_channels, get_targets, get_luns
from .getters import is_there_a_bug_in_target_removal, is_there_a_bug_in_sysfs_async_scanning

logger = getLogger(__name__)

DIRECT_ACCESS_BLOCK_DEVICE = 0
STORAGE_ARRAY_CONTROLLER_DEVICE = 12

@func_logger
def get_luns_from_report_luns(host, channel, target):
    lun_type = get_lun_type(host, channel, target, 0)
    if lun_type is None:
        return set()
    if lun_type not in (DIRECT_ACCESS_BLOCK_DEVICE, STORAGE_ARRAY_CONTROLLER_DEVICE):
        logger.debug("{} Skipping lun type {}".format(getpid(), lun_type))
        return set()
    controller_lun_set = set([0]) # some devices, like IBM FlashSystem, does not return LUN0 in the list
    sg_device = get_scsi_generic_device(host, channel, target, 0)
    return controller_lun_set.union(set(do_report_luns(sg_device).lun_list))

@func_logger
def get_scsi_standard_inquiry(sg_device):
    try:
        standard_inquiry = do_standard_inquiry(sg_device)
        logger.debug("{} Standard inquiry for sg device {}: {}".format(getpid(), sg_device, standard_inquiry))
        return standard_inquiry
    except ScsiCommandFailed:
        logger.error("{} Standard Inquiry {} raised an exception".format(getpid(), sg_device))
        return None

@func_logger
def get_lun_type(host, channel, target, lun):
    sg_device = get_scsi_generic_device(host, channel, target, lun)
    if sg_device is None:
        logger.debug("{} No sg device for {}".format(getpid(), format_hctl(host, channel, target, lun)))
        return None
    standard_inquiry = get_scsi_standard_inquiry(sg_device)
    if standard_inquiry is None:
        msg = "{} scsi generic device {} does not respond to standard inquiry"
        logger.debug(msg.format(getpid(), sg_device.format()))
        return None
    return standard_inquiry.peripheral_device.type

def lun_scan(host, channel, target, lun):
    return get_lun_type(host, channel, target, lun)

@func_logger
def handle_add_devices(host, channel, target, missing_luns):
    if is_there_a_bug_in_sysfs_async_scanning():
        return all(scsi_add_single_device(host, channel, target, lun) for lun in missing_luns)
    return scsi_host_scan(host)

@func_logger
def handle_device_removal(host, channel, target, lun):
    first = remove_device_via_sysfs
    args = (host, channel, target, lun)
    if not first(*args):
        logger.error("{} failed to remove device {}".format(getpid(), format_hctl(host, channel, target, lun)))
        return False
    return True

@func_logger
def target_scan(host, channel, target):
    expected_luns = get_luns_from_report_luns(host, channel, target)
    actual_luns = get_luns(host, channel, target)
    logger.debug("{} expected_luns: {}".format(getpid(), expected_luns))
    logger.debug("{} actual_luns: {}".format(getpid(), actual_luns))
    missing_luns = expected_luns.difference(actual_luns)
    unmapped_luns = actual_luns.difference(expected_luns)
    existing_luns = actual_luns.intersection(expected_luns)
    logger.debug("{} missing_luns: {}".format(getpid(), missing_luns))
    logger.debug("{} unmapped_luns: {}".format(getpid(), unmapped_luns))
    logger.debug("{} existing_luns: {}".format(getpid(), existing_luns))
    if actual_luns and not expected_luns:
        logger.debug("{} target {}:{}:{} was removed".format(getpid(), host, channel, target))
        if is_there_a_bug_in_target_removal():
            return
    if missing_luns:
        handle_add_devices(host, channel, target, missing_luns)
    for lun in unmapped_luns:
        handle_device_removal(host, channel, target, lun)
    for lun in existing_luns:
        if lun == 0:
            # call to get_luns_from_report_luns already called lun_scan for LUN 0,
            # so it is redudtant to do it again
            continue
        lun_scan(host, channel, target, lun)

def try_target_scan(host, channel, target):
    try:
        target_scan(host, channel, target)
    except:
        msg = "Failed to scan target: host={} channel={} target={}. Continuing"
        logger.exception(msg.format(host, channel, target))

@func_logger
def rescan_scsi_host(host):
    from infi.storagemodel.base.gevent_wrapper import start_process
    channels = get_channels(host)
    subprocesses = []
    if not is_there_a_bug_in_sysfs_async_scanning():
        scsi_host_scan(host)
        channels = get_channels(host)
    for channel in channels:
        targets = get_targets(host, channel)
        for target in targets:
            subprocesses.append(start_process(try_target_scan, host, channel, target))
    return subprocesses

@func_logger
def rescan_scsi_hosts():
    subprocesses = []
    for host_number in get_hosts():
        subprocesses.extend(rescan_scsi_host(host_number))
    for subprocess in subprocesses:
        subprocess.join()

