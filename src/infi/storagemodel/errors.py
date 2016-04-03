
from infi.exceptools import InfiException, chain
from infi.pyutils.decorators import wraps
from logging import getLogger


# STORAGEMODEL-301
# When __name_ is used, log function calls say "storagemodel.errors" in the log file, this makes it look like there was an error
logger = getLogger("infi.storagemodel.checker")

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


class RescanError(StorageModelError):
    pass


class DeviceIsBusy(StorageModelError):
    pass

class InsufficientResourcesError(StorageModelError):
    pass


class UnmountFailedDeviceIsBusy(DeviceIsBusy):
    def __init__(self, block_access_path, mount_point):
        super(UnmountFailedDeviceIsBusy, self).__init__(block_access_path, mount_point)

    def __str__(self):
        return "Cannot unmount filesystem {}, device {} is busy".format(self.args[1], self.args[0])


class DeviceError(RescanIsNeeded):
    def __init__(self, *args, **kwargs):
        StorageModelError.__init__(self, *args, **kwargs)

DeviceDisappeared = DeviceError     # backward compatibility

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

class DeviceIsNotLinuxPartition(StorageModelError):
    pass

class ScsiGenericNotLoaded(StorageModelError):
    pass

CHECK_CONDITIONS_TO_CHECK = [
    # 2-tuple of (sense_key, additional_sense_code)
    ('UNIT_ATTENTION', 'POWER ON OCCURRED'),
    ('UNIT_ATTENTION', 'REPORTED LUNS DATA HAS CHANGED'),
    ('UNIT_ATTENTION', 'INQUIRY DATA HAS CHANGED'),
    ('UNIT_ATTENTION', 'POWER ON, RESET, OR BUS DEVICE RESET OCCURRED'),
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

def check_for_scsi_errors(func):
    """
    A decorator for catching SCSI errors from the `infi.asi` layer and converting them to storagemodel errors.
    """
    from infi.asi.errors import AsiOSError, AsiSCSIError, AsiCheckConditionError, AsiRequestQueueFullError
    from sys import exc_info
    @wraps(func)
    def callable(*args, **kwargs):
        try:
            device = args[0]
            logger.debug("Sending SCSI command {!r} for device {!r}".format(func, _safe_repr(device)))
            response = func(*args, **kwargs)
            logger.debug("Got response {!r}".format(response))
            return response
        except AsiCheckConditionError as e:
            if not e.sense_obj:
                msg = "got no sense from device {!r} during {!r}".format(_safe_repr(device), func)
                logger.error(msg, exc_info=exc_info())
                raise chain(DeviceError(msg))
            (key, code) = (e.sense_obj.sense_key, e.sense_obj.additional_sense_code.code_name)
            if (key, code) in CHECK_CONDITIONS_TO_CHECK:
                msg = "device {!r} got {} {}".format(device, key, code)
                logger.debug(msg)
                raise chain(RescanIsNeeded(msg))
            raise
        except AsiRequestQueueFullError as e:
            msg = "got queue full from device {!r} during {!r}".format(_safe_repr(device), func)
            logger.debug(msg)
            raise chain(RescanIsNeeded(msg))
        except AsiSCSIError as error:
            msg = "error with device {!r} during {!r}: {}".format(_safe_repr(device), func, error)
            logger.error(msg)
            raise chain(DeviceError(msg))
        except (IOError, OSError, AsiOSError) as error:
            msg = "error with device {!r} during {!r}".format(_safe_repr(device), func)
            logger.error(msg, exc_info=exc_info())
            raise chain(DeviceError(msg))
    return callable

def check_for_insufficient_resources(func):
    """
    A decorator for retrying on insufficient resources error (management unavailable)
    """
    from infi.asi.errors import AsiCheckConditionError
    from sys import exc_info
    from time import sleep
    @wraps(func)
    def decorator(*args, **kwargs):
        counter = 10
        while counter > 0:
            try:
                msg = "attempting to call {}, {} more retries"
                logger.debug(msg.format(func.__name__, counter))
                return func(*args, **kwargs)
            except AsiCheckConditionError as e:
                (key, code) = (e.sense_obj.sense_key, e.sense_obj.additional_sense_code.code_name)
                msg = "got {} {}".format(key, code)
                if (key, code) != ('ILLEGAL_REQUEST', 'INSUFFICIENT RESOURCES'):
                    logger.error(msg, exc_info=exc_info())
                    raise
                counter -= 1
                if counter == 0:
                    logger.error(msg, exc_info=exc_info())
                    raise chain(InsufficientResourcesError())
                sleep(1)
    return decorator
