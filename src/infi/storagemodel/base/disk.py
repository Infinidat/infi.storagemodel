
from infi.pyutils.lazy import cached_method
from ..errors import StorageModelFindError

# pylint: disable=R0922

class NoSuchDisk(StorageModelFindError):
    pass

class NoPartitionTable(StorageModelFindError):
    pass

class DiskDrive(object):
    @cached_method
    def get_size_in_bytes(self):
        """:returns: the disk size in bytes"""
        return self.get_storage_device().get_size_in_bytes()

    #############################
    # Platform Specific Methods #
    #############################
    def is_empty(self): # pragma: no cover
        """:returns: True if there is a partition table on the disk"""
        raise NotImplementedError()


    def get_partition_table(self): # pragma: no cover
        """:raises: ValueError if there is no partition table on disk

        :returns: A :class:`.PartitionTable` object"""
        raise NotImplementedError()

    def delete_partition_table(self):# pragma: no cover
        """deletes the partition table from the disk"""
        raise NotImplementedError()

    def create_mbr_partition_table(self): # pragma: no cover
        """creates a MBR partition table

        :returns: a :class:`.MBRPartitionTable` object"""
        raise NotImplementedError()

    def create_gpt_partition_table(self): # pragma: no cover
        """creates a GPT partition table

        :returns: a :class:`.GPTPartitionTable` object"""
        raise NotImplementedError()

    @cached_method
    def get_block_access_path(self): # pragma: no cover
        """:returns: the block access path for the disk"""
        raise NotImplementedError()

    @cached_method
    def get_storage_device(self): # pragma: no cover
        """The storage device that is represented by this disk drive.

        :returns: a :class:`.MultipathDevice` or a :class:`.SCSIBlockDevice`"""
        raise NotImplementedError()

class DiskModel(object):
    #############################
    # Platform Specific Methods #
    #############################

    def find_disk_drive_by_block_access_path(self, path): # pragma: no cover
        """:returns: a :class:`.DiskDrive` object that matches the given path.
        :raises: KeyError if no such device is found"""
        # platform implementation
        raise NotImplementedError()

# TODO LIST
#     Platform-specific issues
#         Windows: online/offline disks
#     Uni-directional link from SCSIBlockDevice/MultipathDevice to DiskDrive
#     MBR Extended and logical paritions
#     A more sophisticated method of creating partitions
#     Non-persistent mount_all_persistent_mountpoints-points

