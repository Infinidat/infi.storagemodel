
# pylint: disable=W0102,E1002

class FileSystem(object):
    """Represents a Filesystem that can be formatted and mounted"""

    #############################
    # Platform Specific Methods #
    #############################

    def get_name(self):  # pragma: no cover
        """:returns: the string name of the filesystem"""
        raise NotImplementedError()

    def __str__(self):  # pragma: no cover
        return self.get_name()

    def __repr(self):
        return "{}".format(self.get_name())

    def format(self, block_device, *args, **kwargs):  # pragma: no cover
        """formats the device with this filesystem

        :param block_device: either a :class:`.SCSIBlockDevice` or a :class:`.MultipathDevice` or a :class:`.Partition`
        :raises: :class:`StorageModelError` if the format has failed"""
        raise NotImplementedError()

    def mount(self, block_access_path, mount_point, mount_options_dict={}):  # pragma: no cover
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

    def unmount(self, block_access_path, mount_point):  # pragma: no cover
        """unmount the filesystem from the mount point

        :param mount_point: path to the mount point
        :raises: :class:`NotMounted` if the mount point argument is not a mounted path
        """
        raise NotImplementedError()

    def get_label(self, block_access_path):  # pragma: no cover
        """returns the block device label, or empty string if there's no label
        :raises: :class:`.LabelNotSupported` if not supported by the filesystem
        """
        raise NotImplementedError()

    def set_label(self, block_access_path, label):  # pragma: no cover
        """sets a filesystem label on the specific block device
        :raises: :class:`.InvalidLabel` if the label is too long
        :raises: :class:`.LabelNotSupported` if not supported by the filesystem
        """
        raise NotImplementedError()

    def resize(self, size_in_bytes):  # pragma: no cover
        """resize a filesystem; on platforms that isn't neccessary on, this method does nothing (e.g. Windows)"""
        raise NotImplementedError()
