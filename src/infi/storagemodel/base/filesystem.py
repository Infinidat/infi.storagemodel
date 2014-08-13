
# pylint: disable=W0102,E1002

class FileSystem(object):
    """Represents a Filesystem that can be formatted and mounted"""

    #############################
    # Platform Specific Methods #
    #############################

    def get_name(self):  # pragma: no cover
        """Returns the string name of the filesystem"""
        raise NotImplementedError()

    def __str__(self):  # pragma: no cover
        return self.get_name()

    def __repr(self):
        return "{}".format(self.get_name())

    def format(self, block_device, *args, **kwargs):  # pragma: no cover
        """
        Formats the device with this filesystem.

        **block_device**: either a `infi.storagemodel.base.scsi.SCSIBlockDevice`,
                          `infi.storagemodel.base.multipath.MultipathDevice` or `infi.storagemodel.base.partition.Partition`

        Raises `infi.storagemodel.errors.StorageModelError` if the format has failed
        """
        raise NotImplementedError()

    def mount(self, block_access_path, mount_point, mount_options_dict={}):  # pragma: no cover
        """
        Mounts a device to the mount point, with the given options dictionary.

        **block_device_path**: the block access path of the storage device

        **mount_point**: the path to the mount point

        **mount_options_dict**: filesystem-specific mount options

        Raises `infi.storagemodel.errors.MountPointDoesNotExist` if the mount point does not exist

        Raises `infi.storagemodel.errors.MountPointInUse` if the mount point is in use by another mount

        Raises `infi.storagemodel.errors.AlreadyMounted` if the device is already mounted

        Returns a `infi.storagemodel.mount.Mount` object
        """
        raise NotImplementedError()

    def unmount(self, block_access_path, mount_point):  # pragma: no cover
        """
        Unmount the filesystem from the mount point.

        **mount_point**: path to the mount point

        Raises `infi.storagemodel.errors.NotMounted` if the mount point argument is not a mounted path
        """
        raise NotImplementedError()

    def get_label(self, block_access_path):  # pragma: no cover
        """
        Returns the block device label, or an empty string if there's no label.

        Raises `infi.storagemodel.errors.LabelNotSupported` if operation not supported by the filesystem
        """
        raise NotImplementedError()

    def set_label(self, block_access_path, label):  # pragma: no cover
        """
        Sets a filesystem label on the specific block device.

        Raises `infi.storagemodel.errors.InvalidLabel` if the label is too long

        Raises `infi.storagemodel.errors.LabelNotSupported` if not supported by the filesystem
        """
        raise NotImplementedError()

    def resize(self, size_in_bytes):  # pragma: no cover
        """Resize a filesystem. On platforms where resizing isn't neccessary, this method does nothing (e.g. Windows)"""
        raise NotImplementedError()
