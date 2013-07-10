from ..base import filesystem
from infi.storagemodel.errors import UnmountFailedDeviceIsBusy
# pylint: disable=W0102,W0212


class LinuxFileSystem(filesystem.FileSystem):
    def __init__(self, name):
        super(LinuxFileSystem, self).__init__()
        self._name = name

    def get_name(self):
        return self._name

    def mount(self, block_access_path, mount_point, mount_options_dict={}):
        from infi.mountoolinux.mount.manager import MountManager, MountEntry
        entry = MountEntry(block_access_path, mount_point, self.get_name(), mount_options_dict, 0, 0)
        MountManager().mount_entry(entry)

    def unmount(self, block_access_path, mount_point):
        from infi.mountoolinux.mount.manager import MountManager, MountEntry
        from infi.mountoolinux.mount.errors import BaseMountException
        entry = MountEntry(None, mount_point, None, {}, 0, 0)
        try:
            MountManager().umount_entry(entry)
        except BaseMountException:
            raise UnmountFailedDeviceIsBusy(block_access_path, mount_point)

    def format(self, block_device, *args, **kwargs):
        """currently we ignore args and kwargs"""
        from .partition import LinuxPartition
        if isinstance(block_device, LinuxPartition):
            disk = block_device._containing_disk
            partition = block_device._parted_partition
            number = partition.get_number()
            disk._format_partition(number, self.get_name())
        else:
            from infi.execute import execute
            mkfs = execute(["mkfs.{}", "-F", block_device.get_block_access_path()])
            if mkfs.get_returncode() != 0:
                raise RuntimeError(mkfs.get_stderr())

