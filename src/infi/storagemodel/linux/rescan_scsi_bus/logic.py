from os import getpid
from logging import getLogger
from .utils import func_logger, format_hctl, ScsiCommandFailed
from .scsi import scsi_host_scan, scsi_add_single_device, remove_device_via_sysfs
from .scsi import do_report_luns, do_standard_inquiry, do_test_unit_ready Process
from .getters import get_scsi_generic_device
from .getters import get_hosts, get_channels, get_targets, get_luns
from .getters import is_there_a_bug_in_target_removal, is_there_a_bug_in_sysfs_async_scanning

logger = getLogger(__name__)

@func_logger
def get_luns_from_report_luns(host, channel, target):
    device_exists = lun_scan(host, channel, target, 0)
    controller_lun_set = set([0]) # some devices, like IBM FlashSystem, does not return LUN0 in the list
    if device_exists:
        sg_device = get_scsi_generic_device(host, channel, target, 0)
        return controller_lun_set.union(set(do_report_luns(sg_device).lun_list))
    return set()

@func_logger
def is_scsi_generic_device_online(sg_device):
    def is_responding_to_test_unit_ready():
        try:
            logger.debug("{} Test Unit Ready response on {} is {}".format(getpid(), sg_device, do_test_unit_ready(sg_device)))
            return True
        except ScsiCommandFailed:
            logger.error("{} Test Unit Ready on {} raised an exception".format(getpid(), sg_device))
            return False

    def is_responding_to_standard_inquiry():
        try:
            logger.debug("{} Standard inquiry for sg device {}: {}".format(getpid(), do_standard_inquiry(sg_device), sg_device))
            return True
        except ScsiCommandFailed:
            logger.error("{} Standard Inquiry {} raised an exception".format(getpid(), sg_device))
            return False

    # some devices, like the IBM FlashSystem LUN0, answer to standard inquiry but not to test unit ready
    return any([is_responding_to_test_unit_ready(), is_responding_to_standard_inquiry()])

@func_logger
def lun_scan(host, channel, target, lun):
    sg_device = get_scsi_generic_device(host, channel, target, lun)
    if sg_device is None:
        logger.debug("{} No sg device for {}".format(getpid(), format_hctl(host, channel, target, lun)))
        return False
    if not is_scsi_generic_device_online(sg_device):
        logger.debug("{} scsi generic device {} is not online".format(getpid(), sg_device.format()))
        return False
    return True

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
    channels = get_channels(host)
    subprocesses = []
    if not is_there_a_bug_in_sysfs_async_scanning():
        scsi_host_scan(host)
        channels = get_channels(host)
    for channel in channels:
        targets = get_targets(host, channel)
        for target in targets:
            subprocesses.extend([Process(target=try_target_scan, args=(host, channel, target))])
    return subprocesses

@func_logger
def rescan_scsi_hosts():
    subprocesses = []
    for host_number in get_hosts():
        subprocesses.extend(rescan_scsi_host(host_number))
    for subprocess in subprocesses:
        subprocess.join()

