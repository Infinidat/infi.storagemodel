from logging import getLogger
from infi.execute import execute_assert_success, execute

logger = getLogger(__name__)


def is_iscsiadm_installed():
    from infi.os_info import get_platform_string
    if 'centos' or 'redhat' in get_platform_string():
        logger.debug("checking if iSCSI sw is installed")
        process = execute_assert_success(['rpm', '-qa', '--quiet', 'iscsi-initiator-utils'])
        if process.get_returncode() != 0:
            logger.debug("iscsi sw isn't installed")
            return
        else:
            logger.debug("iscsi sw installed")
            return True


def iscsi_rescan():
    if is_iscsiadm_installed():
        execute(['iscsiadm', '-m', 'session', '--rescan'])
