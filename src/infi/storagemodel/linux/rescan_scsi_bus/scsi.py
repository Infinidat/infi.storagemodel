from logging import getLogger
from os import path, getpid
from infi.pyutils.contexts import contextmanager

from .utils import func_logger, check_for_scsi_errors, asi_context, log_execute, TIMEOUT_IN_SEC
from .utils import ScsiCommandFailed, ScsiCheckConditionError

logger = getLogger(__name__)

def write_to_proc_scsi_scsi(line):
    try:
        with open("/proc/scsi/scsi", "w") as fd:
            fd.write("{}\n".format(line))
    except IOError, err:
        logger.exception("{} IOError {} when writing {!r} to /proc/scsi/scsi".format(getpid(), err, line))
        return False
    return True

@func_logger
def scsi_add_single_device(host, channel, target, lun):
    return write_to_proc_scsi_scsi("scsi add-single-device {} {} {} {}".format(host, channel, target, lun))

@func_logger
def scsi_remove_single_device(host, channel, target, lun):
    return write_to_proc_scsi_scsi("scsi remove-single-device {} {} {} {}".format(host, channel, target, lun))

@func_logger
def scsi_host_scan(host):
    scan_file = "/sys/class/scsi_host/host{}/scan".format(host)
    if path.exists(scan_file):
        try:
            with open(scan_file, "w") as fd:
                fd.write("- - -\n")
        except IOError, err:
            logger.exception("{} IOError {} when writing '- - -' to {}".format(getpid(), err, scan_file))
            return False
        return True
    logger.debug("{} scan file {} does not exist".format(getpid(), scan_file))
    return True

@func_logger
def remove_device_via_sysfs(host, channel, target, lun):
    hctl = "{}:{}:{}:{}".format(host, channel, target, lun)
    delete_file = "/sys/class/scsi_device/{}/device/delete".format(hctl)
    if not path.exists(delete_file):
        logger.debug("{} sysfs delete file {} does not exist".format(getpid(), delete_file))
        return True
    try:
        with open(delete_file, "w") as fd:
            fd.write("1\n")
    except IOError, err:
        logger.exception("{} IOError {} when writing 1 to {}".format(getpid(), err, delete_file))
        return False
    return True

def do_scsi_cdb_with_in_process(queue, sg_device, cdb):
    """ **queue** - either a gipc pipe or a multiprocessing queue """
    from infi.asi.coroutines.sync_adapter import sync_wait

    @check_for_scsi_errors
    def func(sg_device, cdb):
        with asi_context(sg_device) as executer:
            queue.put(sync_wait(cdb.execute(executer)))

    try:
        func(sg_device, cdb)
    except:  # HIP-672 can't use logger in the child process
        try:  # HIP-673 in case we failed to contact the parent process
            queue.put(ScsiCommandFailed())
        except:  # there's no point in raising exception or silencing it because it won't get logged
            pass

def Process(target, args=(), kwargs={}):
    """mocking mutliprocess.Process; uses gipc where available"""
    try:
        from gipc.gipc import start_process as _start_process
    except ImportError:
        from multiprocessing import Process
        def _start_process(target, args, kwargs):
            process = Process(target=target, args=args, kwargs=kwargs)
            process.start()
            return process
    return _start_process(target, args, kwargs)


@contextmanager
def queue():
    from multiprocessing import Queue
    instance = Queue()
    yield instance, instance


@contextmanager
def get_pipe_context():
    try:
        from gipc.gipc import pipe
        _pipe_context = pipe(duplex=True)
    except ImportError:
        _pipe_context = queue()
    with _pipe_context as (reader, writer):
        yield reader, writer

def get_timeout():
    """ Returns the timeout object and exception class"""
    try:  # gipc-based implementation
        from gevent import Timeout
        return Timeout(TIMEOUT_IN_SEC), Timeout
    except ImportError:
        from Queue import Empty
        timeout = TIMEOUT_IN_SEC
        return timeout, Empty

def read_from_queue(reader, subprocess):
    timeout, timeout_class = get_timeout()
    while True:
        try:
            return reader.get(timeout=timeout)
        except IOError, error:
            from errno import EINTR
            # stackoverflow.com/questions/14136195/what-is-the-proper-way-to-handle-in-python-ioerror-errno-4-interrupted-syst
            if error.errno != EINTR:
                return ScsiCommandFailed()
            logger.debug("multiprocessing.Queue.get caught IOError: interrupted system call")
        except timeout_class:
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

@func_logger
def do_scsi_cdb(sg_device, cdb):
    pipe_context = get_pipe_context()
    with pipe_context as (reader, writer):
        logger.debug("{} issuing cdb {!r} on {} with multiprocessing".format(getpid(), cdb, sg_device))
        subprocess = Process(target=do_scsi_cdb_with_in_process, args=(writer, sg_device, cdb,))
        logger.debug("{} multiprocessing pid is {}".format(getpid(), subprocess.pid))
        return_value = read_from_queue(reader, subprocess)
        logger.debug("{} multiprocessing {} returned {!r}".format(getpid(), subprocess.pid, return_value))
        ensure_subprocess_dead(subprocess)
    if isinstance(return_value, ScsiCheckConditionError):
        raise ScsiCheckConditionError(return_value.sense_key, return_value.code_name)
    if isinstance(return_value, ScsiCommandFailed):
        raise ScsiCommandFailed()
    return return_value

@func_logger
def do_report_luns(sg_device):
    from infi.asi.cdb.report_luns import ReportLunsCommand
    cdb = ReportLunsCommand(select_report=0)
    return do_scsi_cdb(sg_device, cdb)

@func_logger
def do_test_unit_ready(sg_device):
    from infi.asi.cdb.tur import TestUnitReadyCommand
    try:
        cdb = TestUnitReadyCommand()
    except ScsiCheckConditionError, error:
        (key, code) = (error.sense_key, error.code_name)
        if key == 'NOT_READY':
            return False
        if (key, code) == ('ILLEGAL_REQUEST', 'INVALID COMMAND OPERATION CODE'):
            return False
        raise
    return do_scsi_cdb(sg_device, cdb)

@func_logger
def do_standard_inquiry(sg_device):
    from infi.asi.cdb.inquiry.standard import StandardInquiryCommand
    cdb = StandardInquiryCommand()
    return do_scsi_cdb(sg_device, cdb)

@func_logger
def is_udevadm_exist():
    return path.exists("/sbin/udevadm")

@func_logger
def execute_udevadm():
    return log_execute(["/sbin/udevadm", "settle"], TIMEOUT_IN_SEC*3)

@func_logger
def is_udevsettle_exist():
    return path.exists("/sbin/udevsettle")

@func_logger
def execute_udevsettle():
    return log_execute(["/sbin/udevsettle"], TIMEOUT_IN_SEC*3)
