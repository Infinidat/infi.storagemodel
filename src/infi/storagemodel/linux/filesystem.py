from ..unix import filesystem
from infi.storagemodel.errors import UnmountFailedDeviceIsBusy, LabelNotSupported, InvalidLabel, DeviceIsNotLinuxPartition


class LinuxFileSystem(filesystem.UnixFileSystem):
    def __init__(self, name):
        super(LinuxFileSystem, self).__init__(name)

    def _get_mount_manager(self):
        from infi.mount_utils.linux import LinuxMountManager
        return LinuxMountManager()

    def _create_mount_entry(self, block_access_path, mount_point, mount_options_dict={}):
        from infi.mount_utils.linux.mount import LinuxMountEntry
        entry = LinuxMountEntry(block_access_path, mount_point, self.get_name(), mount_options_dict, 0, 0)
        return entry

    def format(self, block_device, *args, **kwargs):
        from .partition import LinuxPartition
        if isinstance(block_device, LinuxPartition):
            disk = block_device._containing_disk
            partition = block_device._parted_partition
            number = partition.get_number()
            disk._format_partition(number, self.get_name(), **kwargs)
        else:
            raise DeviceIsNotLinuxPartition(block_device.__str__())

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
