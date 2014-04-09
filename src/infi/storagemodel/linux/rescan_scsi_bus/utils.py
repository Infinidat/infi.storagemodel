from logging import getLogger
from os import getpid
from infi.exceptools import chain
from infi.pyutils.contexts import contextmanager
from infi.pyutils.decorators import wraps

CHECK_CONDITIONS_NOT_WORTH_RETRY = [
    ('ILLEGAL_REQUEST', 'LOGICAL UNIT NOT SUPPORTED'),
    ('ILLEGAL_REQUEST', 'INVALID FIELD IN CDB'),
    ('ILLEGAL_REQUEST', 'INVALID COMMAND OPERATION CODE'),
]

SEC = 1000
TIMEOUT_IN_SEC = 3
TIMEOUT = SEC * TIMEOUT_IN_SEC

logger = getLogger(__name__)

class ScsiCommandFailed(Exception):
    pass

class ScsiCheckConditionError(ScsiCommandFailed):
    def __init__(self, sense_key, code_name):
        super(ScsiCheckConditionError, self).__init__(sense_key, code_name)
        self.sense_key = sense_key
        self.code_name = code_name

def func_logger(func):
    @wraps(func)
    def decorator(*args, **kwargs):
        format_args = ', '.join([str(item) for item in args])
        format_kwargs = ', '.join(["{}={!r}".format(str(key), str(value)) for key, value in kwargs.items()])
        logger.debug("{} --> {}({}, {})".format(getpid(), func.__name__, format_args, format_kwargs))
        result = func(*args, **kwargs)
        try:
            logger.debug("{} <-- return {!r} | {}".format(getpid(), result, func.__name__))
        except Exception, err:
            logger.exception("{} <-- {} raise {} | {}".format(getpid(), err, func.___name__))
            raise
        return result
    return decorator

@func_logger
def log_execute(args, timeout_in_seconds=None):
    from infi.execute import execute_async, CommandTimeout
    pid = execute_async(args)
    try:
        pid.wait(timeout_in_seconds)
    except CommandTimeout:
        pid.kill(9)
    return pid.get_pid()

@contextmanager
def asi_context(sg_device):
    import os
    import infi.asi
    import infi.asi.unix
    handle = infi.asi.unix.OSFile(os.open("/dev/{}".format(sg_device), os.O_RDWR))
    executer = infi.asi.create_platform_command_executer(handle, timeout=TIMEOUT)
    try:
        yield executer
    finally:
        handle.close()

def check_for_scsi_errors(func):
    from infi.asi.errors import AsiOSError, AsiSCSIError, AsiCheckConditionError
    @wraps(func)
    def decorator(*args, **kwargs):
        counter = 10
        while counter > 0:
            try:
                sg_device, cdb = args
                msg = "{} attempting to send {} to sg device {}, {} more retries"
                logger.debug(msg.format(getpid(), func.__name__, sg_device, counter))
                response = func(*args, **kwargs)
                return func(*args, **kwargs)
            except AsiCheckConditionError, e:
                (key, code) = (e.sense_obj.sense_key, e.sense_obj.additional_sense_code.code_name)
                msg = "{} sg device {} got {} {}".format(getpid(), sg_device, key, code)
                logger.warn(msg)
                counter -= 1
                if (key, code) in CHECK_CONDITIONS_NOT_WORTH_RETRY or counter == 0:
                    raise ScsiCheckConditionError(key, code)
            except (IOError, OSError, AsiOSError, AsiSCSIError), error:
                msg = "{} sg device {} got unrecoverable error {} during {}"
                logger.error(msg.format(getpid(), sg_device, error, cdb))
                counter = 0
        raise chain(ScsiCommandFailed())
    return decorator

def format_hctl(host, channel, target, lun):
    return "{}:{}:{}:{}".format(host, channel, target, lun)
