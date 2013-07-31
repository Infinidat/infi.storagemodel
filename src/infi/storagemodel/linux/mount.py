from ..base import mount
from infi.pyutils.lazy import cached_method

# pylint: disable=W0223,W0212

class LinuxMountManager(mount.MountManager):
    def _translate_mount_object(self, hidden_object):
        return LinuxMount(hidden_object)

    def _translate_filesystem_object(self, filesystem_name):
        from .filesystem import LinuxFileSystem
        return LinuxFileSystem(filesystem_name)

    @cached_method
    def get_mounts(self):
        from infi.mountoolinux.mount.manager import MountManager
        return [LinuxMount(entry) for entry in MountManager().get_mounts_from_mtab()]

    def is_mount_point_in_use(self, mount_point):
        from infi.mountoolinux.mount.manager import MountManager
        return MountManager().is_path_mounted(mount_point)

    def is_device_mounted(self, device):
        from infi.mountoolinux.mount.manager import MountManager
        return MountManager().is_fs_mounted(device)

    @cached_method
    def get_available_file_systems(self):
        from infi.mountoolinux.mount.manager import MountManager
        return [self._translate_filesystem_object(name) for name in MountManager().get_supported_file_systems()]
        
    @cached_method
    def get_creatable_file_systems(self):
        from infi.mountoolinux.mount.manager import MountManager
        return [self._translate_filesystem_object(name) for name in MountManager().get_creatable_file_systems()]

    @cached_method
    def get_recommended_file_system(self):
        return self._translate_filesystem_object("ext3")

class LinuxMount(mount.Mount):
    def __init__(self, mount_entry):
        super(LinuxMount, self).__init__()
        self._entry = mount_entry

    def get_block_access_path(self):
        return self._entry.get_fsname()

    def get_mount_options(self):
        return self._entry.get_opts()

    def get_mount_point(self):
        return self._entry.get_dirname()

    def get_filesystem(self):
        from .filesystem import LinuxFileSystem
        return LinuxFileSystem(self._entry.get_type())

class LinuxPersistentMount(LinuxMount, mount.PersistentMount):
    pass

class LinuxMountRepository(mount.MountRepository):
    def get_all_persistent_mounts(self):
        from infi.mountoolinux.mount.manager import MountManager
        return [LinuxPersistentMount(entry) for entry in MountManager().get_mounts_from_fstab()]

    def remove_persistent_mountpoint(self, persistent_mount):
        from infi.mountoolinux.mount.manager import MountManager
        entry = persistent_mount._entry
        if MountManager().is_entry_in_fstab(entry):
            MountManager().remove_entry_from_fstab(entry)

    def add_persistent_mountpoint(self, mount): # pylint: disable=W0621
        from infi.mountoolinux.mount.manager import MountManager
        entry = mount._entry
        if not MountManager().is_entry_in_fstab(entry):
            MountManager().add_entry_to_fstab(entry)
