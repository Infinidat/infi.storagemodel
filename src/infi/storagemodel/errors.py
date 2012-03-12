
from infi.exceptools import InfiException
from infi.pyutils.decorators import wraps

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

class DeviceDisappeared(RescanIsNeeded):
    def __init__(self, *args, **kwargs):
        StorageModelError.__init__(self, *args, **kwargs)
    pass

class TimeoutError(StorageModelError):
    """Timeout error"""
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

def check_for_scsi_errors(func):
    from infi.asi.errors import AsiOSError
    from infi.asi import AsiCheckConditionError
    @wraps(func)
    def callable(*args, **kwargs):
        try:
            device = args[0]
            return func(*args, **kwargs)
        except (IOError, OSError, AsiOSError), error:
            raise chain(DeviceDisappeared("device {!r} disappeared during {!r}".format(device, func)))
        except AsiCheckConditionError, e:
            (key, code) = (e.sense_obj.sense_key, e.sense_obj.additional_sense_code.code_name)
            if (key, code) == ('UNIT_ATTENTION', 'POWER ON OCCURRED'):
                raise chain(RescanIsNeeded("device {!r} got {} {}".format(device, key, code)))
            if (key, code) == ('UNIT_ATTENTION', 'REPORTED LUNS DATA HAS CHANGED'):
                raise chain(RescanIsNeeded("device {!r} got {} {}".format(device, key, code)))
            if (key, code) == ('UNIT_ATTENTION', 'LOGICAL UNIT NOT SUPPORTED'):
                raise chain(DeviceDisappeared("device {!r} got {} {}".format(device, key, code)))
            else:
                raise
    return callable

