from __future__ import print_function

from logging import getLogger
from os import getpid
from infi.traceback import traceback_decorator
from .utils import func_logger
from .logic import rescan_scsi_hosts

logger = getLogger(__name__)


@traceback_decorator
@func_logger
def main():
    from infi.storagemodel.base.gevent_wrapper import reinit
    reinit()
    try:
        rescan_scsi_hosts()
        return 0
    except Exception as err:
        logger.exception("{} Unhandled exception in rescan_scsi_bus: {}".format(getpid(), err))
        return 1


@func_logger
def console_script():
    from platform import system
    from sys import stderr
    from logging import DEBUG, basicConfig
    if system() != "Linux":
        print("This script is for Linux only")
    basicConfig(stream=stderr, level=DEBUG)
    from infi.storagemodel import get_storage_model
    get_storage_model().rescan_and_wait_for(wait_for_completion=True)
