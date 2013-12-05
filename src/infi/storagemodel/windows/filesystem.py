
from ..base import filesystem, partition
from infi.storagemodel.errors import UnmountFailedDeviceIsBusy, LabelNotSupported
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
        try:
            MountManager().remove_mount_point(block_access_path, mount_point)
        except:  # diskmanagement module is a thin wrapper on top ctypes, does not differntiate error codes
            raise UnmountFailedDeviceIsBusy(block_access_path, mount_point)

    def _get_mount_point_for_labels(self, block_access_path):
        mount_points = []
        for volume_guid, list_of_mount_points in MountManager().get_mounts_of_all_volumes().items():
            if volume_guid != block_access_path:
                continue
            mount_points.extend(list_of_mount_points)
        if not mount_points:
            raise LabelNotSupported("label can only be managed for mounted volumes")
        return mount_points[0]

    def set_label(self, block_access_path, label):
        mount_point = self._get_mount_point_for_labels(block_access_path)
        MountManager().set_volume_label(mount_point, label)

    def get_label(self, block_access_path):
        mount_point = self._get_mount_point_for_labels(block_access_path)
        return MountManager().get_volume_label(mount_point)

    def resize(self, size_in_bytes):  # pragma: no cover
        pass
