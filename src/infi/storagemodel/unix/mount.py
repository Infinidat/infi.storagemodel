from ..base import mount
from infi.pyutils.lazy import cached_method

class UnixMountManager(mount.MountManager):
    """A wrapper for mount-utils mount interface"""
    def _get_mount_manager(self):
        from infi.mount_utils import get_mount_manager
        return get_mount_manager()

    @cached_method
    def get_mounts(self):
        return [self._get_mount_object(entry) for entry in self._get_mount_manager().get_mounts_from_mtab()]

    def is_mount_point_in_use(self, mount_point):
        return self._get_mount_manager().is_path_mounted(mount_point)

    def is_device_mounted(self, device):
        return self._get_mount_manager().is_fs_mounted(device)

    @cached_method
    def get_available_file_systems(self):
        return [self._get_file_system_object(name) for name in self._get_mount_manager().get_supported_file_systems()]

    @cached_method
    def get_creatable_file_systems(self):
        return [self._get_file_system_object(name) for name in self._get_mount_manager().get_creatable_file_systems()]

    def _get_mount_object(self, entry):
        raise NotImplementedError()

    def _get_file_system_object(self, fsname):
        raise NotImplementedError()

    @cached_method
    def get_recommended_file_system(self):
        raise NotImplementedError()

class UnixMount(mount.Mount):
    """A wrapper for mount-utils mount entry"""
    def __init__(self, mount_entry):
        super(UnixMount, self).__init__()
        self._entry = mount_entry

    def get_block_access_path(self):
        return self._entry.get_fsname()

    def get_mount_options(self):
        return self._entry.get_opts()

    def get_mount_point(self):
        return self._entry.get_dirname()

    def get_filesystem(self):
        raise NotImplementedError()

    def get_entry(self):
        return self._entry

class UnixPersistentMount(mount.PersistentMount):
    pass

class UnixMountRepository(mount.MountRepository):
    def _get_mount_manager(self):
        from infi.mount_utils import get_mount_manager
        return get_mount_manager()

    def get_all_persistent_mounts(self):
        return [self._get_persistent_mount_object(entry) for entry in self._get_mount_manager().get_mounts_from_fstab()]

    def remove_persistent_mountpoint(self, persistent_mount):
        entry = persistent_mount._entry
        if self._get_mount_manager().is_entry_in_fstab(entry):
            self._get_mount_manager().remove_entry_from_fstab(entry)

    def add_persistent_mountpoint(self, mount):
        entry = mount._entry
        if not self._get_mount_manager().is_entry_in_fstab(entry):
            self._get_mount_manager().add_entry_to_fstab(entry)

    def _get_persistent_mount_object(self, entry):
        raise NotImplementedError()