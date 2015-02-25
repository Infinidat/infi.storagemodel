
from ..base import mount, partition
from infi.diskmanagement import MountManager
# pylint: disable=W0212,E1002

class WindowsMount(mount.Mount):
    def __init__(self, filesystem, block_access_path, mount_point):
        super(WindowsMount, self).__init__()
        self._filesystem = filesystem
        self._block_access_path = block_access_path
        self._mount_point = mount_point

    def get_block_access_path(self):
        return self._block_access_path

    def get_filesystem(self):
        return self._filesystem

    def get_mount_options(self):
        return {}

    def get_mount_point(self):
        return self._mount_point

class WindowsMountManager(mount.MountManager):
    def __init__(self):
        super(WindowsMountManager, self).__init__()
        self.mount_manager = MountManager()

    def get_mounts(self):
        # TODO we only support NTFS
        mounts = []
        for volume_guid, list_of_mount_points in MountManager().get_mounts_of_all_volumes().items():
            for mount_point in list_of_mount_points:
                mounts.append(WindowsMount(self.get_recommended_file_system(), volume_guid, mount_point))
        return mounts

    def is_mount_point_in_use(self, mount_point):
        return any(mount_point == mount.get_mount_point() for mount in self.get_mounts())

    def is_device_mounted(self, device):
        # TODO we only support partitions
        assert isinstance(device, partition.Partition)
        return len(device._get_volume().get_mount_points()) == 0

    def get_available_file_systems(self):
        return [self.get_recommended_file_system(), ]

    def get_creatable_file_systems(self):
        return [self.get_recommended_file_system(), ]

    def get_recommended_file_system(self):
        from .filesystem import WindowsFileSystem
        return WindowsFileSystem("NTFS")

    def get_available_drive_letters(self):
        return MountManager().get_avaialable_drive_letters()

    def disable_auto_mount(self):
        MountManager().disable_auto_mount()

    def enable_auto_mount(self):
        MountManager().enable_auto_mount()

    def is_auto_mount(self):
        return MountManager().is_auto_mount()

class WindowsMountRepository(mount.MountRepository):
    def get_all_persistent_mounts(self):
        return [WindowsPersistentMount(mount) for mount in WindowsMountManager().get_mounts()]

    def remove_persistent_mountpoint(self, persistent_mount):
        if all(mount.get_block_access_path() != item.get_block_access_path() and
               mount.get_mount_point() != item.get_mount_point() for item in self.get_all_persistent_mounts()):
                return
        return WindowsMountManager().unmount(persistent_mount)

    def add_persistent_mountpoint(self, mount):
        if any(mount.get_block_access_path() == item.get_block_access_path() and
               mount.get_mount_point() == item.get_mount_point() for item in self.get_all_persistent_mounts()):
                return
        return WindowsMountManager().mount(mount)

class WindowsPersistentMount(mount.PersistentMount):
    def __init__(self, hidden_object):
        super(WindowsPersistentMount, self).__init__()
        self._hidden_object = hidden_object
        for attr in ["get_block_access_path", "get_mount_options", "get_mount_point", "get_filesystem"]:
            setattr(self, attr, getattr(hidden_object, attr))
