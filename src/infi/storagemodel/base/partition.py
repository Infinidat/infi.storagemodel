from infi.pyutils.lazy import cached_method
from ..errors import StorageModelError

class PartitionTableNotEmpty(StorageModelError):
    pass

class Partition(object):
    @cached_method
    def get_size_in_bytes(self): # pragma: no cover
        """:returns: the size in bytes of the partition"""
        raise NotImplementedError()

    @cached_method
    def get_block_access_path(self): # pragma: no cover
        """:returns: the block access path for the partition"""
        raise NotImplementedError()

    @cached_method
    def get_containing_disk(self): # pragma: no cover
        """:returns: the disk drive that holds the partition
        :rtype: :class:`.DiskDrive`"""
        raise NotImplementedError()

    @cached_method
    def get_current_filesystem(self): # pragma: no cover
        """Calls :class:`.FileSystemFactoryImpl"""
        raise NotImplementedError()

class MBRPartition(Partition):
    # pylint: disable=W0223
    # This methods below are overriden by platform-specific implementations
    pass

class PrimaryPartition(MBRPartition):
    # pylint: disable=W0223
    # This methods below are overriden by platform-specific implementations
    pass

class ExtendedPartition(MBRPartition):
    # pylint: disable=W0223
    # This methods below are overriden by platform-specific implementations
    pass

class LogicalPartition(MBRPartition):
    # pylint: disable=W0223
    # This methods below are overriden by platform-specific implementations
    pass

class GUIDPartition(Partition):
    # pylint: disable=W0223
    # This methods below are overriden by platform-specific implementations
    pass

class PartitionTable(object):
    @cached_method
    def is_empty(self):
        """:returns: True if there are no partitions in the partition table"""
        return len(self.get_partitions()) == 0

    #############################
    # Platform Specific Methods #
    #############################

    @classmethod
    def create_partition_table(cls, disk_drive): # pragma: no cover
        """Changes are written immediately on disk
        Partition table is re-read and cache for the current object is cleared
        
        :returns: The newly created :class:`.Partition` object"""
        raise NotImplementedError()

    @cached_method
    def get_partitions(self): # pragma: no cover
        """returns: a list of :class:`.Partition` objects inside the partition table"""
        raise NotImplementedError()

    @cached_method
    def get_disk_drive(self): # pragma: no cover
        """:returns: the disk drive that holds the partition
        :rtype: :class:`.DiskDrive`"""
        raise NotImplementedError()

    def create_partition_for_whole_table(self, file_system_object): # pragma: no cover
        """Changes are written immediately on disk
        Partition table is re-read and cache for the current object is cleared
        
        :returns: a :class:`.Partition` object"""
        # This is one of the places where things can get complicated
        # I just want to be able to create a new partition in an empty partition table
        raise NotImplementedError()

class MBRPartitionTable(PartitionTable):
    # This methods below are overriden by platform-specific implementations
    # pylint: disable=W0223
    pass

class GPTPartitionTable(PartitionTable):
    # pylint: disable=W0223
    # This methods below are overriden by platform-specific implementations
    pass

