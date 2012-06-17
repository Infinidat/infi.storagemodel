import os
from contextlib import contextmanager

from ..base import StorageModel
from infi.pyutils.lazy import cached_method, cached_function

from logging import getLogger
logger = getLogger(__name__)

POSSIBLE_RESCAN_SCSI_BUS_FILENAMES = ["rescan-scsi-bus", "rescan-scsi-bus.sh"]
POSSIBLE_PATH_LOCATIONS = ["/sbin", "/bin", "/usr/bin", "/usr/sbin"]
POSSIBLE_PARTPROBE_FILENAME = ['partprobe']

CHMOD_777 = 33261

def _write_an_executable_copy_of_builtin_rescan_script():
    from os import chmod, write, close
    from pkg_resources import resource_stream
    from tempfile import mkstemp
    fd, path = mkstemp(prefix='rescan-scsi-bus.sh_', text=True)
    write(fd, resource_stream(__name__, 'rescan-scsi-bus.sh').read())
    close(fd)
    chmod(path, CHMOD_777)
    return path

def _locate_file_in_path(possible_filenames):
    for filename in possible_filenames:
        for base in (POSSIBLE_PATH_LOCATIONS + os.environ["PATH"].split(':')):
            script = os.path.join(base, filename)
            if os.path.exists(script) and os.access(script, os.X_OK):
                return script
    # no script found
    return None

@cached_function
def _locate_rescan_script():
    from os import access, environ, X_OK, chmod
    from os.path import exists, join
    # STORAGEMODEL-138 because the os-supplied rescan-scsi-bus.sh is too slow, we use a modified version of it
    return _write_an_executable_copy_of_builtin_rescan_script()

def _call_partprobe(env=None, sync=False):
    from infi.execute import execute
    command = [_locate_file_in_path(POSSIBLE_PARTPROBE_FILENAME), ]
    execute(command, env=env) if sync else _daemonize_and_run(command, env, False)

def _is_ubuntu():
    from platform import linux_distribution
    distname = linux_distribution()[0].lower()
    return distname in ["ubuntu", ]

def _get_all_host_bus_adapter_numbers():
    from infi.hbaapi import get_ports_collection
    return [port.hct[0] for port in get_ports_collection().get_ports()]

def _call_rescan_script(env=None, sync=False, shell=True):
    """for testability purposes, we want to call execute with no environment variables, to mock the effect
    that the script does not exist"""
    from infi.exceptools import chain
    from infi.execute import execute
    from ..errors import StorageModelError
    rescan_script = _locate_rescan_script()
    hba_numbers = [str(host_number) for host_number in _get_all_host_bus_adapter_numbers()]
    if rescan_script is None:
        raise StorageModelError("no rescan-scsi-bus script found") # pylint: disable=W0710
    try:
        logger.info("Calling rescan-scsi-bus.sh")
        if shell:
            command = "{} --remove {} | logger".format(rescan_script, ' '.join(hba_numbers))
        else:
            command = [rescan_script, '--remove'] + hba_numbers
        execute(command, shell=shell, env=env) if sync else _daemonize_and_run(command, env, shell)
    except Exception:
        logger.exception("failed to initiate rescan")
        raise chain(StorageModelError("failed to initiate rescan"))

def _daemonize_and_run(command, env, shell):
    from daemon import basic_daemonize
    from infi.execute import execute
    first_child_pid = os.fork()
    if first_child_pid != 0:
        os.waitpid(first_child_pid, 0)
    else:
        basic_daemonize()
        script = execute(command, env=env, shell=shell)
        logger.info("rescan-scsi-bus.sh finished with return code {}".format(script.get_returncode()))
        os._exit(0)

class LinuxStorageModel(StorageModel):
    @cached_method
    def _get_sysfs(self):
        from .sysfs import Sysfs
        return Sysfs()

    def _create_scsi_model(self):
        from .scsi import LinuxSCSIModel
        return LinuxSCSIModel(self._get_sysfs())

    def _create_native_multipath_model(self):
        from .native_multipath import LinuxNativeMultipathModel
        return LinuxNativeMultipathModel(self._get_sysfs())

    def _create_disk_model(self):
        from .disk import LinuxDiskModel
        return LinuxDiskModel()

    def _create_mount_manager(self):
        from .mount import LinuxMountManager
        return LinuxMountManager()

    def _create_mount_repository(self):
        from .mount import LinuxMountRepository
        return LinuxMountRepository()

    def initiate_rescan(self, wait_for_completion=True):
        """the first attempt will be to use rescan-scsi-bus.sh, which comes out-of-the-box in redhat distributions,
        and from the debian packager scsitools.
        If and when we'll encounter a case in which this script doesn't work as expected, we will port it to Python
        and modify it accordingly.
        """
        _call_rescan_script(sync=wait_for_completion)
        _call_partprobe(sync=wait_for_completion)

def is_rescan_script_exists():
    return _locate_rescan_script() is not None
