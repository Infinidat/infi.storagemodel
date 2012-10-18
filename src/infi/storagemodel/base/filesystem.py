
# pylint: disable=W0102,E1002

class FileSystem(object):
    """Represents a Filesystem that can be formatted and mounted"""

    #############################
    # Platform Specific Methods #
    #############################

    def get_name(self): # pragma: no cover
        """:returns: the string name of the filesystem"""
        raise NotImplementedError()

    def __str__(self): # pragma: no cover
        return self.get_name()

    def __repr(self):
        return "{}".format(self.get_name())

    def format(self, block_device, *args, **kwargs): # pragma: no cover
        """formats the device with this filesystem
        
        :param block_device: either a :class:`.SCSIBlockDevice` or a :class:`.MultipathDevice` or a :class:`.Partition`
        :raises: :class:`StorageModelError` if the format has failed"""
        raise NotImplementedError()

    def mount(self, block_access_path, mount_point, mount_options_dict={}): # pragma: no cover
        """mounts a device to the mount point, with the given options dictionary
        
        :param block_device_path: the block access path of the storage device 
        :param mount_point: the path to the mount point
        :param mount_options_dict: filesystem-specific mount options
        :raises: :class:`.MountPointDoesNotExist` if the mount point does not exist
        :raises: :class:`.MountPointInUse` if the mount point is in use by another mount
        :raises: :class:`.AlreadyMounted` if the device is already mounted
        :returns: a :class:`Mount` object
        """
        raise NotImplementedError()

    def unmount(self, block_access_path, mount_point): # pragma: no cover
        """unmount the filesystem from the mount point
        
        :param mount_point: path to the mount point
        :raises: :class:`NotMounted` if the mount point argument is not a mounted path
        """
        raise NotImplementedError()

class FileSystemFactoryImpl(object):
    #############################
    # Platform Specific Methods #
    #############################

    def get_filesystem_for_partition(self, device, filesystem_object):
        """:returns: a :class:`.FileSystem` object that is on top of a block device
        :param device: Either a :class:`.MultipathDevice` or a :class:`.SCSIBlockDevice` or :class:`.Partition`
        :param filesystem_object: a :class:`.FileSystem` obeject"""
        class FileSystemOnPartition(type(filesystem_object)):
            _device = device

            def format(self, *args, **kwargs):
                return super(FileSystemOnPartition, self).format(self._device, *args, **kwargs)

            def mount(self, mount_point, mount_options_dict={}):
                return super(FileSystemOnPartition, self).mount(self._device.get_block_access_path(),
                                                              mount_point, mount_options_dict)
        return FileSystemOnPartition()

FileSystemFactory = FileSystemFactoryImpl()
