from infi.pyutils.decorators import wraps
from logging import getLogger


logger = getLogger(__name__)


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
        except AsiCheckConditionError, e:
            if not e.sense_obj:
                msg = "got no sense from device {!r} during {!r}".format(_safe_repr(device), func)
                logger.error(msg, exc_info=exc_info())
                raise chain(DeviceDisappeared(msg))
            (key, code) = (e.sense_obj.sense_key, e.sense_obj.additional_sense_code.code_name)
            if (key, code) in CHECK_CONDITIONS_TO_CHECK:
                msg = "device {!r} got {} {}".format(device, key, code)
                logger.debug(msg)
                raise chain(RescanIsNeeded(msg))
            raise
        except AsiRequestQueueFullError, e:
            msg = "got queue full from device {!r} during {!r}".format(_safe_repr(device), func)
            logger.debug(msg)
            raise chain(RescanIsNeeded(msg))
        except AsiSCSIError as error:
            msg = "device {!r} disappeared during {!r}: {}".format(_safe_repr(device), func, error)
            logger.error(msg)
            raise chain(DeviceDisappeared(msg))
        except (IOError, OSError, AsiOSError), error:
            msg = "device {!r} disappeared during {!r}".format(_safe_repr(device), func)
            logger.error(msg, exc_info=exc_info())
            raise chain(DeviceDisappeared(msg))
    return callable



class Utils(object):
    #############################
    # Platform Specific Methods #
    #############################

    def get_free_space(self, path):  # pragma: no cover
        """Returns the free space in bytes, inside the filesystem of a given path"""
        # platform implementation
        raise NotImplementedError()
