from os import getpid
from logging import getLogger
from .utils import func_logger, format_hctl, ScsiCommandFailed
from .scsi import scsi_host_scan, scsi_add_single_device, scsi_remove_single_device, remove_device_via_sysfs
from .scsi import do_report_luns, do_standard_inquiry, do_test_unit_ready
from .getters import is_device_exist, get_scsi_generic_device
from .getters import get_channels, get_targets, get_luns
from .getters import is_there_a_bug_in_target_removal, is_there_a_bug_in_sysfs_async_scanning

logger = getLogger(__name__)

@func_logger
def get_luns_from_report_luns(host, channel, target):
    device_exists = lun_scan(host, channel, target, 0)
    if device_exists:
        sg_device = get_scsi_generic_device(host, channel, target, 0)
        return set(do_report_luns(sg_device).lun_list)
    return set()

@func_logger
def is_scsi_generic_device_online(sg_device):
    try:
        do_test_unit_ready(sg_device)
    except ScsiCommandFailed:
        logger.error("{} Test Unit Ready on {} raised an exception".format(getpid(), sg_device))
        return False
    try:
        standard_inquiry = do_standard_inquiry(sg_device)
    except ScsiCommandFailed:
        logger.error("{} Standard Inquiry {} raised an exception".format(getpid(), sg_device))
        return False
    logger.debug("{} Standard inquiry for sg device {}: {}".format(getpid(), standard_inquiry, sg_device))
    if standard_inquiry.peripheral_device.qualifier != 0:
        return False
    return True

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
        return all([scsi_add_single_device(host, channel, target, lun) for lun in missing_luns])
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
        logger.info("{} target {}:{}:{} was removed".format(getpid(), host, channel, target))
        if is_there_a_bug_in_target_removal():
            return
    if missing_luns:
        handle_add_devices(host, channel, target, missing_luns)
    for lun in unmapped_luns:
        handle_device_removal(host, channel, target, lun)
    for lun in existing_luns:
        lun_scan(host, channel, target, lun)

@func_logger
def rescan_scsi_host(host):
    channels = get_channels(host)
    if not channels and not is_there_a_bug_in_sysfs_async_scanning():
        # no devices from this scsi host, yet
        scsi_host_scan(host)
        channels = get_channels(host)
    for channel in channels:
        targets = get_targets(host, channel)
        for target in targets:
            try:
                target_scan(host, channel, target)
            except:
                msg = "Failed to scan target: host={} channel={} target={}. Continuing"
                logger.exception(msg.format(host, channel, target))

@func_logger
def rescan_scsi_hosts(host_numbers):
    for host_number in host_numbers:
        rescan_scsi_host(host_number)
