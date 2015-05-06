from ..unix import mount
from infi.pyutils.lazy import cached_method

# pylint: disable=W0223,W0212

class SolarisMountManager(mount.UnixMountManager):
    def _get_file_system_object(self, fsname):
        from .filesystem import SolarisFileSystem
        return SolarisFileSystem(fsname)

    @cached_method
    def get_recommended_file_system(self):
        return self._get_file_system_object("zfs")

    def _get_mount_object(self, entry):
        return SolarisMount(entry)

class SolarisMount(mount.UnixMount):
    def __init__(self, mount_entry):
        super(SolarisMount, self).__init__(mount_entry)
        self._entry = mount_entry

    def get_filesystem(self):
        from .filesystem import SolarisFileSystem
        return SolarisFileSystem(self._entry.get_typename())

class SolarisPersistentMount(SolarisMount, mount.UnixPersistentMount):
    pass

class SolarisMountRepository(mount.UnixMountRepository):
    def _get_persistent_mount_object(self, entry):
        return SolarisPersistentMount(entry)
