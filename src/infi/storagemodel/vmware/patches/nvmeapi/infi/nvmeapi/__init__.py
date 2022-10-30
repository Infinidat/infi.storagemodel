__nvmeapi = None
__nvme_software_initiator = None


def get_nvmeapi():
    global __nvmeapi
    if __nvmeapi is None:
        __nvmeapi = _get_platform_specific_nvmeapi()
    return __nvmeapi


def get_nvme_software_initiator():
    global __nvme_software_initiator
    if __nvme_software_initiator is None:
        __nvme_software_initiator = _get_platform_specific_nvme_software_initiator()
    return __nvme_software_initiator


def _get_platform_specific_nvmeapi():
    from infi.os_info import get_platform_string
    platform = get_platform_string()
    if platform.startswith('linux'):
        from . import linux
        return linux.Linuxnvmeapi()
    else:
        raise ImportError("not supported on this platform")


def _get_platform_specific_nvme_software_initiator():
    from infi.os_info import get_platform_string
    platform = get_platform_string()
    if platform.startswith('linux'):
        from . import linux
        return linux.LinuxSoftwareInitiator()
    else:
        raise ImportError("not supported on this platform")
