from ..unix import filesystem
from infi.storagemodel.errors import UnmountFailedDeviceIsBusy, LabelNotSupported, InvalidLabel


class SolarisFileSystem(filesystem.UnixFileSystem):
    def __init__(self, name):
        super(SolarisFileSystem, self).__init__(name)

    def _get_mount_manager(self):
        from infi.mount_utils.solaris import SolarisMountManager
        return SolarisMountManager()

    def _create_mount_entry(self, block_access_path, mount_point, mount_options_dict={}):
        from infi.mount_utils.solaris.mount import SolarisMountEntry
        entry = SolarisMountEntry(block_access_path, mount_point, self.get_name(), mount_options_dict, 0, '-')

    def format(self, block_device, *args, **kwargs):
        # We don't implement it right now.
        raise NotImplementedError()

    def get_label(self, block_access_path):  # pragma: no cover
        raise NotImplementedError()

    def set_label(self, block_access_path, label):  # pragma: no cover
        raise NotImplementedError()
