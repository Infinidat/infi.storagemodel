from logging import getLogger
from infi.execute import execute

logger = getLogger(__name__)


def is_iscsiadm_installed():
    from infi.os_info import get_platform_string
    if 'centos' in get_platform_string() or 'redhat' in get_platform_string():
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
