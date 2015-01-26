from infi.storagemodel.base.utils import Utils

import logging  # pylint: disable=W0403
logger = logging.getLogger(__name__)

WAIT_TIME = 120


class LinuxUtils(Utils):
    def get_free_space(self, path):
        from os import statvfs
        stat_res = statvfs(path)
        return stat_res.f_frsize * stat_res.f_bavail


def execute_command(cmd, check_returncode=True, timeout=WAIT_TIME):  # pragma: no cover
    from infi.execute import execute
    logger.info("executing {}".format(cmd))
    process = execute(cmd)
    process.wait(WAIT_TIME)
    logger.info("execution returned {}".format(process.get_returncode()))
    logger.debug("stdout: {}".format(process.get_stdout()))
    logger.debug("stderr: {}".format(process.get_stderr()))
    if check_returncode and process.get_returncode() != 0:
        formatted_cmd = cmd if isinstance(cmd, basestring) else repr(' '.join(cmd))
        raise RuntimeError("execution of {} failed".format(formatted_cmd))
    return process
