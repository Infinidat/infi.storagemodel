from logging import getLogger
from infi.execute import execute
from infi.os_info import system_is_rhel_based

logger = getLogger(__name__)


def is_iscsiadm_installed():
    if system_is_rhel_based():
        logger.debug("checking if iSCSI sw is installed")
        process = execute(['/bin/rpm', '-q', '--quiet', 'iscsi-initiator-utils'])
        if process.get_returncode() != 0:
            logger.debug("iscsi sw isn't installed")
            return False
        else:
            logger.debug("iscsi sw installed")
            return True
    return False


def iscsi_rescan():
    if is_iscsiadm_installed():
        execute(['/sbin/iscsiadm', '-m', 'session', '--rescan'])
