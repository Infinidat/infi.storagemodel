
from infi.pyutils.lazy import cached_method, clear_cache

class Mount(object):
    """Represents a mount in the operating system"""

    #############################
    # Platform Specific Methods #
    #############################

    def get_block_access_path(self): # pragma: no cover
        """:returns the block access path of the device to be mounted"""
        raise NotImplementedError()

    def get_filesystem(self): # pragma: no cover
        """:returns: the :class:`.FileSystem` object that requested to be mounted"""
        raise NotImplementedError()

    def get_mount_options(self): # pragma: no cover
        """:returns: filesystem-specifc mount options"""
        raise NotImplementedError()

    def get_mount_point(self): # pragma: no cover
        """:returns: the mount point"""
        raise NotImplementedError()

class PersistentMount(Mount):
    # pylint: disable=W0223
    # This methods below are overriden by platform-specific implementations
    pass

class MountRepository(object):
    """Holds all the persistent mounts configurations"""

    #############################
    # Platform Specific Methods #
    #############################

    def get_all_persistent_mounts(self):
        """:returns: A list :class:`.PersistentMount` objects"""
        raise NotImplementedError()

    def remove_persistent_mountpoint(self, persistent_mount): # pragma: no cover
        """removes a persistent mount
        
        :param: a :class:`.PersistentMount` object"""
        raise NotImplementedError()

    def add_persistent_mountpoint(self, mount): # pragma: no cover
        """creates a :class:`.PersistentMount" object for the mount object and registers it
        
        :param: a :class:`Mount` object
        """
        raise NotImplementedError()

class MountManager(object):
    def mount(self, mount_object):
        """A utility function that calls the :method:`.FileSystem.mount` method of a :class:`.FileSystem` object
        
        :param mount_object: a :class:`.Mount` object
        """
        block_access_path = mount_object.get_block_access_path()
        mount_point = mount_object.get_mount_point()
        mount_options = mount_object.get_mount_options()
        mount_object.get_filesystem().mount(block_access_path, mount_point, mount_options)
        clear_cache(self)

    def unmount(self, mount_object):
        """A utility function that calls the :method:`.FileSystem.unmount` method of a :class:`.FileSystem` object
        
        :param mount_object: a :class:`.Mount` object
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
        """:returns: A list of live :class:`.Mount` objects"""
        raise NotImplementedError() # pragma: no cover

    def is_mount_point_in_use(self, mount_point): # pragma: no cover
        """:returns: True if the mount point is in use"""
        raise NotImplementedError()

    def is_device_mounted(self, device): # pragma: no cover
        """:returns: True if the device is already mounted"""
        raise NotImplementedError()

    @cached_method
    def get_available_file_systems(self): # pragma: no cover
        """:returns: a list of :class:`.FileSystem` objects"""
        raise NotImplementedError()

    @cached_method
    def get_creatable_file_systems(self): # pragma: no cover
        """:returns: a list of :class:`.FileSystem` objects"""
        raise NotImplementedError()

    @cached_method
    def get_recommended_file_system(self): # pragma: no cover
        """:returns: a :class:`.FileSystem` objects"""
        raise NotImplementedError()
