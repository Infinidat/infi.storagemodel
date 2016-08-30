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
        format_args = ', '.join([repr(item) for item in args])
        format_kwargs = ', '.join(["{}={!r}".format(repr(key), repr(value)) for key, value in kwargs.items()])
        logger.debug("{} --> {}({}, {})".format(getpid(), func.__name__, format_args, format_kwargs))
        result = func(*args, **kwargs)
        try:
            logger.debug("{} <-- return {!r} | {}".format(getpid(), result, func.__name__))
        except Exception as err:
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
    from infi.asi import create_platform_command_executer, create_os_file
    handle = create_os_file("/dev/{}".format(sg_device))
    executer = create_platform_command_executer(handle, timeout=TIMEOUT)
    try:
        yield executer
    finally:
        handle.close()

def check_for_scsi_errors(func):
    from infi.asi.errors import AsiOSError, AsiSCSIError, AsiCheckConditionError
    from infi.asi.cdb.report_luns import UnsupportedReportLuns
    @wraps(func)
    def decorator(*args, **kwargs):
        counter = 10
        while counter > 0:
            try:
                sg_device, cdb = args
                msg = "{} attempting to send {} to sg device {}, {} more retries"
                logger.debug(msg.format(getpid(), func.__name__, sg_device, counter))
                response = func(*args, **kwargs)
                return response
            except AsiCheckConditionError as e:
                (key, code) = (e.sense_obj.sense_key, e.sense_obj.additional_sense_code.code_name)
                msg = "{} sg device {} got {} {}".format(getpid(), sg_device, key, code)
                logger.warn(msg)
                counter -= 1
                if (key, code) in CHECK_CONDITIONS_NOT_WORTH_RETRY or counter == 0:
                    raise ScsiCheckConditionError(key, code)
            except (IOError, OSError, AsiOSError, AsiSCSIError) as error:
                msg = "{} sg device {} got unrecoverable error {} during {}"
                logger.error(msg.format(getpid(), sg_device, error, cdb))
                counter = 0
            except UnsupportedReportLuns as error:
                msg = "{} sg device {} has unsupported luns report: {}"
                logger.error(msg.format(getpid(), sg_device, error))
                raise ScsiCommandFailed()
        raise chain(ScsiCommandFailed())
    return decorator

def format_hctl(host, channel, target, lun):
    return "{}:{}:{}:{}".format(host, channel, target, lun)

def read_from_queue(reader, subprocess):
    from infi.storagemodel.base.gevent_wrapper import get_timeout
    timeout, timeout_exception = get_timeout(TIMEOUT_IN_SEC)
    while True:
        try:
            return reader.get(timeout=timeout)
        except IOError as error:
            from errno import EINTR
            # stackoverflow.com/questions/14136195/what-is-the-proper-way-to-handle-in-python-ioerror-errno-4-interrupted-syst
            if error.errno != EINTR:
                return ScsiCommandFailed()
            logger.debug("multiprocessing.Queue.get caught IOError: interrupted system call")
        except timeout_exception:
            msg = "{} multiprocessing {} did not return within {} seconds timeout"
            logger.error(msg.format(getpid(), subprocess.pid, TIMEOUT_IN_SEC))
            return ScsiCommandFailed()
        except:
            msg = "{} multiprocessing {} error"
            logger.exception(msg.format(getpid(), subprocess.pid))
            return ScsiCommandFailed()

def ensure_subprocess_dead(subprocess):
    from os import kill
    pid = subprocess.pid
    if subprocess.is_alive() and pid:
        logger.debug("{} terminating multiprocessing {}".format(getpid(), pid))
        try:
            kill(pid, 9)
        except:
            logger.debug("{} failed to terminate multiprocessing {}".format(getpid(), pid))
    subprocess.join()

def put_result_in_queue(func):
    @wraps(func)
    def inner_func(queue, *args, **kwargs):
        try:
            queue.put(func(*args, **kwargs))
        except Exception as error:
            try:
                queue.put(error)
            except:
                queue.ScsiCommandFailed()
    return inner_func

def call_in_subprocess(func, *args, **kwargs):
    from infi.storagemodel.base.gevent_wrapper import start_process, get_pipe_context
    pipe_context = get_pipe_context()
    with pipe_context as (reader, writer):
        logger.debug("{} calling {}(args={!r}, kwargs={!r}) on with multiprocessing".format(getpid(), func, args, kwargs))
        subprocess = start_process(put_result_in_queue(func), writer, *args, **kwargs)
        logger.debug("{} multiprocessing pid is {}".format(getpid(), subprocess.pid))
        return_value = read_from_queue(reader, subprocess)
        logger.debug("{} multiprocessing {} returned {!r}".format(getpid(), subprocess.pid, return_value))
        ensure_subprocess_dead(subprocess)
    return return_value
