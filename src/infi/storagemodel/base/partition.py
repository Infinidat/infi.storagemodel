from infi.pyutils.lazy import cached_method
from ..errors import StorageModelError

class PartitionTableNotEmpty(StorageModelError):
    pass

class Partition(object):
    """ Base class for representing patitions """

    @cached_method
    def get_size_in_bytes(self):  # pragma: no cover
        """Returns the size in bytes of the partition"""
        raise NotImplementedError()

    @cached_method
    def get_block_access_path(self):  # pragma: no cover
        """Returns the block access path for the partition"""
        raise NotImplementedError()

    @cached_method
    def get_containing_disk(self):  # pragma: no cover
        """Returns the `infi.storagemodel.base.disk.DiskDrive` that holds the partition"""
        raise NotImplementedError()

    @cached_method
    def get_current_filesystem(self):  # pragma: no cover
        """Returns the current filesystem"""
        raise NotImplementedError()

    def resize(self, size_in_bytes):
        """Resizes the partition"""
        raise NotImplementedError()

class MBRPartition(Partition):
    """ Base class for partitions in an MBR partition table """
    # pylint: disable=W0223
    # The methods below are overriden by platform-specific implementations
    pass

class PrimaryPartition(MBRPartition):
    """ Represents a primary partition in an MBR partition table """
    # pylint: disable=W0223
    # The methods below are overriden by platform-specific implementations
    pass

class ExtendedPartition(MBRPartition):
    """ Represents an extended partition in an MBR partition table """
    # pylint: disable=W0223
    # The methods below are overriden by platform-specific implementations
    pass

class LogicalPartition(MBRPartition):
    """ Represents a logical partition in an MBR partition table """
    # pylint: disable=W0223
    # The methods below are overriden by platform-specific implementations
    pass

class GUIDPartition(Partition):
    """ Represents a partition in a GUID partition table (GPT) """
    # pylint: disable=W0223
    # The methods below are overriden by platform-specific implementations
    pass

class PartitionTable(object):
    """ Base class for representing patition tables """

    @cached_method
    def is_empty(self):
        """Returns True if there are no partitions in the partition table"""
        return len(self.get_partitions()) == 0

    #############################
    # Platform Specific Methods #
    #############################

    @classmethod
    def create_partition_table(cls, disk_drive, alignment_in_bytes=None):  # pragma: no cover
        """Creates a partition table of the requested class on the given `infi.storagemodel.base.disk.DiskDrive`.
        No partitions are created inside the partition table.

        Changes are written immediately on disk. The partition table is re-read and the cache for the current object is cleared.

        Returns The newly created `infi.storagemodel.base.partition.Partition` object"""
        raise NotImplementedError()

    @cached_method
    def get_partitions(self):  # pragma: no cover
        """Returns a list of `infi.storagemodel.base.partition.Partition` objects inside the partition table"""
        raise NotImplementedError()

    @cached_method
    def get_disk_drive(self):  # pragma: no cover
        """Returns the `infi.storagemodel.base.disk.DiskDrive` that holds the partition"""
        raise NotImplementedError()

    def create_partition_for_whole_table(self, file_system_object, alignment_in_bytes=None):  # pragma: no cover
        """Creates a partition that fills the entire drive. The partition is set to use the given filesystem,
        but does not get formatted by this method.

        Changes are written immediately on disk. The partition table is re-read and the cache for the current object is cleared.

        Returns a `infi.storagemodel.base.partition.Partition` object"""
        # This is one of the places where things can get complicated
        # I just want to be able to create a new partition in an empty partition table
        raise NotImplementedError()

class MBRPartitionTable(PartitionTable):
    """ Represents a Master Boot Record partition table """
    # The methods below are overriden by platform-specific implementations
    # pylint: disable=W0223
    pass

class GUIDPartitionTable(PartitionTable):
    """ Represents a GUID partition table """
    # pylint: disable=W0223
    # The methods below are overriden by platform-specific implementations
    pass
