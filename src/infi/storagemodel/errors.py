from infi.exceptools import InfiException, chain
from .base.utils import check_for_scsi_errors

from logging import getLogger
logger = getLogger(__name__)

# pylint: disable=E1002
# InfiException inherits from Exception

class StorageModelError(InfiException):
    """Base Exception class for this module """
    pass


class StorageModelFindError(StorageModelError):
    """Find error"""
    pass


class RescanIsNeeded(StorageModelError):
    pass


class DeviceIsBusy(StorageModelError):
    pass


class UnmountFailedDeviceIsBusy(DeviceIsBusy):
    def __init__(self, block_access_path, mount_point):
        super(UnmountFailedDeviceIsBusy, self).__init__(block_access_path, mount_point)

    def __str__(self):
        return "Cannot unmount filesystem {}, device {} is busy".format(self.args[1], self.args[0])


class DeviceDisappeared(RescanIsNeeded):
    def __init__(self, *args, **kwargs):
        StorageModelError.__init__(self, *args, **kwargs)
    pass

class TimeoutError(StorageModelError):
    """Timeout error"""
    pass

class MultipathDaemonTimeoutError(TimeoutError):
    pass

class NotMounted(StorageModelError):
    def __init__(self, mount_point):
        super(NotMounted, self).__init__("path {!r} is not being used by any mount".format(mount_point))

class AlreadyMounted(StorageModelError):
    def __init__(self, mount_point):
        super(AlreadyMounted, self).__init__("mount point {!r} is already mounted".format(mount_point))

class MountPointDoesNotExist(StorageModelError):
    def __init__(self, mount_point):
        super(MountPointDoesNotExist, self).__init__("mount point {!r} does not exist".format(mount_point))

class MountPointInUse(StorageModelError):
    def __init__(self, mount_point):
        super(MountPointInUse, self).__init__("mount point {!r} is already in use".format(mount_point))

class InvalidLabel(StorageModelError):
    pass

class LabelNotSupported(StorageModelError):
    pass


CHECK_CONDITIONS_TO_CHECK = [
    # 2-tuple of (sense_key, additional_sense_code)
    ('UNIT_ATTENTION', 'POWER ON OCCURRED'),
    ('UNIT_ATTENTION', 'REPORTED LUNS DATA HAS CHANGED'),
    ('UNIT_ATTENTION', 'INQUIRY DATA HAS CHANGED'),
    ('UNIT_ATTENTION', 'BUS DEVICE RESET FUNCTION OCCURRED'),
    ('UNIT_ATTENTION', 'ASYMMETRIC ACCESS STATE CHANGED'),
    ('UNIT_ATTENTION', 'CAPACITY DATA HAS CHANGED'),
    ('ILLEGAL_REQUEST', 'LOGICAL UNIT NOT SUPPORTED'),
    ('ABORTED_COMMAND', 'COMMANDS CLEARED BY DEVICE SERVER'),
]

def _safe_repr(obj):
    try:
        return repr(obj)
    except:
        return object.__repr__(obj)
