
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
        """Returns the disk size in bytes"""
        return self.get_storage_device().get_size_in_bytes()

    #############################
    # Platform Specific Methods #
    #############################
    def is_empty(self):  # pragma: no cover
        """Returns True if the disk has no partition table."""
        raise NotImplementedError()

    def get_partition_table(self):  # pragma: no cover
        """
        Returns the disk's partition table (`infi.storagemodel.base.partition.PartitionTable`).
        Raises `ValueError` if there is no partition table on disk.
        """
        raise NotImplementedError()

    def delete_partition_table(self):  # pragma: no cover
        """Deletes the partition table from the disk"""
        raise NotImplementedError()

    def create_mbr_partition_table(self, alignment_in_bytes=None):  # pragma: no cover
        """Creates an MBR partition table and returns it (`infi.storagemodel.base.partition.MBRPartitionTable`)"""
        raise NotImplementedError()

    def create_guid_partition_table(self, alignment_in_bytes=None):  # pragma: no cover
        """Creates a GUID partition table and returns it (`infi.storagemodel.base.partition.GUIDPartitionTable`)"""
        raise NotImplementedError()

    @cached_method
    def get_block_access_path(self):  # pragma: no cover
        """Returns the block access path for the disk"""
        raise NotImplementedError()

    @cached_method
    def get_storage_device(self):  # pragma: no cover
        """
        Returns the storage device that is represented by this disk drive - either
        a `infi.storagemodel.base.multipath.MultipathDevice` or `infi.storagemodel.base.scsi.SCSIBlockDevice`
        """
        raise NotImplementedError()

    @cached_method
    def get_block_access_paths_for_partitions(self):
        try:
            return [item.get_block_access_path() for item in self.get_partition_table().get_partitions()]
        except (NoPartitionTable, NoSuchDisk, IndexError):
            return []


class DiskModel(object):
    #############################
    # Platform Specific Methods #
    #############################

    def find_disk_drive_by_block_access_path(self, path):  # pragma: no cover
        """
        Returns a `infi.storagemodel.base.disk.DiskDrive` object that matches the given path,
        or raises a KeyError if no such device is found
        """
        # platform implementation
        raise NotImplementedError()

# TODO LIST
#     Platform-specific issues
#         Windows: online/offline disks
#     Uni-directional link from SCSIBlockDevice/MultipathDevice to DiskDrive
#     MBR Extended and logical paritions
#     A more sophisticated method of creating partitions
#     Non-persistent mount_all_persistent_mountpoints-points
