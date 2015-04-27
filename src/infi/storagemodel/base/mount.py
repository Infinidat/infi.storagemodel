"""
This is the mounts layer of the storagemodel.

Example 1 - listing mounts:

    #!python
    >>> from infi.storagemodel import get_storage_model
    >>> mgr = get_storage_model().get_mount_manager()
    >>> for mount in mgr.get_mounts():
    ...     print  print '{:10} {:30} {}'.format(mount.get_block_access_path(),
    ...                                          mount.get_mount_point(),
    ...                                          mount.get_mount_options())
    /dev/sda1  /                              {'rw': True}
    proc       /proc                          {'rw': True}
    sysfs      /sys                           {'rw': True}
    devpts     /dev/pts                       {'gid': 5, 'rw': True, 'mode': 620}
    tmpfs      /dev/shm                       {'rw': True}
    none       /proc/sys/fs/binfmt_misc       {'rw': True}

Example 2 - checking mountpoint availability:

    #!python
    >>> mgr.is_mount_point_in_use('/sys')
    True
    >>> mgr.is_mount_point_in_use('/foo')
    False

Example 3 - getting filesystem types:

    #!python
    >>> print [fs.get_name() for fs in mgr.get_available_file_systems()]
    ['hfsplus', 'ext4', 'ext3', 'ext2', 'iso9660', 'hfs', 'vfat', 'tmpfs']
    >>> print [fs.get_name() for fs in mgr.get_creatable_file_systems()]
    ['ext4', 'ext3', 'ext2', 'vfat']

"""

from infi.pyutils.lazy import cached_method, clear_cache

class Mount(object):
    """Represents a non-persistent mount in the operating system"""

    #############################
    # Platform Specific Methods #
    #############################

    def get_block_access_path(self):  # pragma: no cover
        """Returns the block access path of the device to be mounted"""
        raise NotImplementedError()

    def get_filesystem(self):  # pragma: no cover
        """Returns the `infi.storagemodel.base.filesystem.FileSystem` object that requested to be mounted"""
        raise NotImplementedError()

    def get_mount_options(self):  # pragma: no cover
        """Returns filesystem-specific mount options"""
        raise NotImplementedError()

    def get_mount_point(self):  # pragma: no cover
        """Returns the mount point"""
        raise NotImplementedError()

class PersistentMount(Mount):
    """Represents a persistent mount in the operating system"""

    # pylint: disable=W0223
    # The methods below are overriden by platform-specific implementations
    pass

class MountRepository(object):
    """Holds all the persistent mounts configurations"""

    #############################
    # Platform Specific Methods #
    #############################

    def get_all_persistent_mounts(self):
        """Returns A list of `infi.storagemodel.base.mount.PersistentMount` objects"""
        raise NotImplementedError()

    def remove_persistent_mountpoint(self, persistent_mount):  # pragma: no cover
        """removes a persistent mount

        **persistent_mount**: a `infi.storagemodel.base.mount.PersistentMount` object"""
        raise NotImplementedError()

    def add_persistent_mountpoint(self, mount):  # pragma: no cover
        """creates a `infi.storagemodel.base.mount.PersistentMount` object for the mount object and registers it.

        **mount**: a `infi.storagemodel.base.mount.Mount` object
        """
        raise NotImplementedError()

class MountManager(object):
    """Provides access to mount-related operations"""

    def mount(self, mount_object):
        """A utility function that calls the :meth:`.FileSystem.mount` method of a `infi.storagemodel.base.filesystem.FileSystem` object

        **mount_object**: a `infi.storagemodel.base.mount.Mount` object
        """
        block_access_path = mount_object.get_block_access_path()
        mount_point = mount_object.get_mount_point()
        mount_options = mount_object.get_mount_options()
        mount_object.get_filesystem().mount(block_access_path, mount_point, mount_options)
        clear_cache(self)

    def unmount(self, mount_object):
        """A utility function that calls the :meth:`.FileSystem.unmount` method of a `infi.storagemodel.base.filesystem.FileSystem` object

        **mount_object**: a `infi.storagemodel.base.mount..Mount` object
        """
        mount_point = mount_object.get_mount_point()
        block_access_path = mount_object.get_block_access_path()
        mount_object.get_filesystem().unmount(block_access_path, mount_point)
        clear_cache(self)

    #############################
    # Platform Specific Methods #
    #############################

    @cached_method
    def get_mounts(self):
        """Returns A list of live `infi.storagemodel.base.mount.Mount` objects"""
        raise NotImplementedError()  # pragma: no cover

    def is_mount_point_in_use(self, mount_point):  # pragma: no cover
        """Returns True if the mount point is in use"""
        raise NotImplementedError()

    def is_device_mounted(self, device):  # pragma: no cover
        """Returns True if the device is already mounted"""
        raise NotImplementedError()

    @cached_method
    def get_available_file_systems(self):  # pragma: no cover
        """Returns a list of `infi.storagemodel.base.filesystem.FileSystem` objects"""
        raise NotImplementedError()

    @cached_method
    def get_creatable_file_systems(self):  # pragma: no cover
        """Returns a list of `infi.storagemodel.base.filesystem.FileSystem` objects"""
        raise NotImplementedError()

    @cached_method
    def get_recommended_file_system(self):  # pragma: no cover
        """Returns a `infi.storagemodel.base.filesystem.FileSystem` objects"""
        raise NotImplementedError()
