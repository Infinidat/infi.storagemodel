
from ..base import filesystem, partition
from infi.diskmanagement import MountManager

# pylint: disable=W0212,E1002

class WindowsFileSystem(filesystem.FileSystem):
    def __init__(self, name):
        super(WindowsFileSystem, self).__init__()
        self._name = name

    def get_name(self):
        return self._name

    def format(self, block_device, *args, **kwargs):
        # TODO we only support partitions
        assert isinstance(block_device, partition.Partition)
        volume = block_device._get_volume()
        kwargs["file_system"] = self._name
        volume.format(*args, **kwargs)

    def mount(self, block_access_path, mount_point, mount_options_dict={}):
        from .mount import WindowsMount
        # TODO we only support partitions
        assert 'Volume' in block_access_path
        MountManager().add_volume_mount_point(block_access_path, mount_point)
        return WindowsMount(self, block_access_path, mount_point)

    def unmount(self, block_access_path, mount_point):
        MountManager().remove_mount_point(block_access_path, mount_point)
