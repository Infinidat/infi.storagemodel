from logging import getLogger
from os import path, getpid
from time import sleep

from .utils import func_logger, check_for_scsi_errors, asi_context, log_execute, ScsiCommandFailed, TIMEOUT_IN_SEC

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
    from infi.asi.coroutines.sync_adapter import sync_wait
    from sys import exc_info

    @check_for_scsi_errors
    def func(sg_device, cdb):
        with asi_context(sg_device) as executer:
            queue.put(sync_wait(cdb.execute(executer)))
    try:
        func(sg_device,cdb )
    except:
        logger.exception("{} multiprocessing caught unhandled exception".format(getpid()))
        queue.put(ScsiCommandFailed())

@func_logger
def do_scsi_cdb(sg_device, cdb):
    from multiprocessing import Process, Queue
    from Queue import Empty
    queue = Queue()
    logger.debug("{} issuing cdb {!r} on {} with multiprocessing".format(getpid(), cdb, sg_device))
    subprocess = Process(target=do_scsi_cdb_with_in_process, args=(queue, sg_device, cdb,))
    subprocess.start()
    logger.debug("{} multiprocessing pid is {}".format(getpid(), subprocess.pid))
    try:
        return_value = queue.get(timeout=TIMEOUT_IN_SEC)
    except Empty:
        msg = "{} multiprocessing {} did not return within {} seconds timeout"
        logger.error(msg.format(getpid(), subprocess.pid, TIMEOUT_IN_SEC))
        return_value = ScsiCommandFailed()
    logger.debug("{} multiprocessing {} returned {!r}".format(getpid(), subprocess.pid, return_value))
    if not subprocess.is_alive():
        logger.error("{} terminating multiprocessing {}".format(getpid(), subprocess.pid))
        try:
            subprocess.terminate()
        except:
            logger.error("{} failed to terminate multiprocessing {}".format(getpid(), subprocess.pid))
    if isinstance(return_value, ScsiCommandFailed):
        raise ScsiCommandFailed()
    return return_value

@func_logger
def do_report_luns(sg_device):
    from infi.asi.cdb.report_luns import ReportLunsCommand
    cdb = ReportLunsCommand(select_report=1)
    return do_scsi_cdb(sg_device, cdb)

@func_logger
def do_test_unit_ready(sg_device):
    from infi.asi.cdb.tur import TestUnitReadyCommand
    cdb = TestUnitReadyCommand()
    return do_scsi_cdb(sg_device, cdb)

@func_logger
def do_standard_inquiry(sg_device):
    from infi.asi.cdb.inquiry.standard import StandardInquiryCommand
    cdb = StandardInquiryCommand()
    return do_scsi_cdb(sg_device, cdb)

@func_logger
def sync_file_systems():
    return log_execute(["sync"], TIMEOUT_IN_SEC)

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

@func_logger
def udevadm_settle():
    if is_udevadm_exist():
        return execute_udevadm()
    elif is_udevsettle_exist():
        return execute_udevsettle()
    sleep(20)
    return 0

@func_logger
def partprobe():
    return log_execute(["/sbin/partprobe"], TIMEOUT_IN_SEC)
