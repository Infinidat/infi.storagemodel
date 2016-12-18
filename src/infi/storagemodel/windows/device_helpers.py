from logging import getLogger

MPIO_BUS_DRIVER_INSTANCE_ID = u"Root\\MPIO\\0000".lower()
logger = getLogger(__name__)


def is_disk_drive_managed_by_windows_mpio(disk_drive):
    try:
        return disk_drive.parent._instance_id.lower() == MPIO_BUS_DRIVER_INSTANCE_ID
    except KeyError:
        logger.debug("failed to get parent instance id for disk drive {!r}, assuming its not mpio".format(disk_drive))
        return False


def safe_get_physical_drive_number(device):
    try:
        return device.get_physical_drive_number()
    except KeyError:
        logger.debug("failed to get physical drive number for {!r} ({!r})".format(device, device._device_object))
        return -1


def is_disk_visible_in_device_manager(disk_drive):
    try:
        return not disk_drive.is_hidden()
    except KeyError:
        return False


def is_device_installed(device):
    try:
        device.hardware_ids
        return True
    except:
        return False
