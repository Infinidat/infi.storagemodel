from ..base import filesystem
from infi.storagemodel.errors import UnmountFailedDeviceIsBusy, LabelNotSupported, InvalidLabel
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
        from infi.mountoolinux.mount.errors import MountException
        entry = MountEntry(None, mount_point, None, {}, 0, 0)
        try:
            MountManager().umount_entry(entry)
        except MountException:
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

    def _e2label(self, block_access_path, new_label=None):
        from infi.execute import execute
        args = ["e2label", block_access_path]
        if new_label is not None:
            args.append(new_label)
        pid = execute(args)
        if pid.get_returncode() != 0:
            raise LabelNotSupported()
        return pid.get_stdout().strip()

    def get_label(self, block_access_path):  # pragma: no cover
        return self._e2label(block_access_path)

    def set_label(self, block_access_path, label):  # pragma: no cover
        before = self.get_label(block_access_path)
        self._e2label(block_access_path, label)
        after = self.get_label(block_access_path)
        if after != label:
            # e2label truncates labels
            self._e2label(block_access_path, before)
            raise InvalidLabel()
