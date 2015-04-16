from ..unix import mount
from infi.pyutils.lazy import cached_method

# pylint: disable=W0223,W0212

class LinuxMountManager(mount.UnixMountManager):
    def _get_file_system_object(self, fsname):
        from .filesystem import LinuxFileSystem
        return LinuxFileSystem(fsname)

    @cached_method
    def get_recommended_file_system(self):
        return self._get_file_system_object("ext3")

    def _get_mount_object(self, entry):
        return LinuxMount(entry)

class LinuxMount(mount.UnixMount):
    def __init__(self, mount_entry):
        super(LinuxMount, self).__init__(mount_entry)
        self._entry = mount_entry

    def get_filesystem(self):
        from .filesystem import LinuxFileSystem
        return LinuxFileSystem(self._entry.get_typename())

class LinuxPersistentMount(LinuxMount, mount.UnixPersistentMount):
    pass

class LinuxMountRepository(mount.UnixMountRepository):
    def _get_persistent_mount_object(self, entry):
        return LinuxPersistentMount(entry)
