from ..base import filesystem
from infi.storagemodel.errors import UnmountFailedDeviceIsBusy, LabelNotSupported, InvalidLabel
# pylint: disable=W0102,W0212


class UnixFileSystem(filesystem.FileSystem):
    def __init__(self, name):
        super(UnixFileSystem, self).__init__()
        self._name = name

    def get_name(self):
        return self._name

    def _get_mount_manager(self):
    	raise NotImplementedError()

    def _create_mount_entry(self, block_access_path, mount_point, mount_options_dict={}):
    	raise NotImplementedError()

    def mount(self, block_access_path, mount_point, mount_options_dict={}):
        entry = self._create_mount_entry(block_access_path, mount_point, mount_options_dict)
        self._get_mount_manager().mount_entry(entry)

    def unmount(self, block_access_path, mount_point):
        from infi.mount_utils.exceptions import MountException
        entry = self._create_mount_entry(None, mount_point, {})
        try:
            self._get_mount_manager().umount_entry(entry)
        except MountException:
            raise UnmountFailedDeviceIsBusy(block_access_path, mount_point)

    def format(self, block_device, *args, **kwargs):
        raise NotImplementedError()

    def get_label(self, block_access_path):  # pragma: no cover
        raise NotImplementedError()

    def set_label(self, block_access_path, label):  # pragma: no cover
        raise NotImplementedError()
