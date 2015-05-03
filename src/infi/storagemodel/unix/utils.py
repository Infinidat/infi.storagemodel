from infi.storagemodel.base.utils import Utils

import logging  # pylint: disable=W0403
logger = logging.getLogger(__name__)

WAIT_TIME = 120


class UnixUtils(Utils):
    def get_free_space(self, path):
        from os import statvfs
        stat_res = statvfs(path)
        return stat_res.f_frsize * stat_res.f_bavail


def execute_command(cmd, check_returncode=True, timeout=WAIT_TIME):  # pragma: no cover
    from infi.execute import execute
    logger.info("executing {}".format(cmd))
    process = execute(cmd)
    process.wait(WAIT_TIME)
    logger.info("execution of cmd {} (pid {}) returned {}".format(cmd, process.get_id(), process.get_returncode()))
    logger.debug("stdout: {}".format(process.get_stdout()))
    logger.debug("stderr: {}".format(process.get_stderr()))
    if check_returncode and process.get_returncode() != 0:
        formatted_cmd = cmd if isinstance(cmd, basestring) else repr(' '.join(cmd))
        raise RuntimeError("execution of {} failed".format(formatted_cmd))
    return process

def execute_command_safe(cmd, *args, **kwargs):
    try:
        cmd = cmd.split()
        return execute_command(cmd, *args, **kwargs).get_stdout()
    except OSError as e:
        if e.errno not in (2, 20): # file not found, not a directory
            logger.exception("{} failed with unknown reason", cmd)
        return ""
