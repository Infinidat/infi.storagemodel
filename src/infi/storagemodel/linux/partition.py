from infi.pyutils.lazy import cached_method, clear_cache
from ..base import partition

# pylint: disable=W0212

class LinuxPartition(partition.Partition):
    def __init__(self, containing_disk, parted_partition):
        super(LinuxPartition, self).__init__()
        self._parted_partition = parted_partition
        self._containing_disk = containing_disk

    @cached_method
    def get_size_in_bytes(self):
        return self._parted_partition.get_size_in_bytes()

    @cached_method
    def get_block_access_path(self):
        return self._parted_partition.get_access_path()

    @cached_method
    def get_containing_disk(self):
        return self._containing_disk

    @cached_method
    def get_current_filesystem(self):
        from .filesystem import LinuxFileSystem
        filesystem_type = self._parted_partition.get_filesystem_name()
        return LinuxFileSystem(filesystem_type)

class LinuxPrimaryPartition(LinuxPartition, partition.PrimaryPartition):
    # pylint: disable=W0223
    # The methods below are overriden by platform-specific implementations
    pass

class LinuxExtendedPartition(LinuxPartition, partition.ExtendedPartition):
    # pylint: disable=W0223
    # The methods below are overriden by platform-specific implementations
    pass

class LinuxLogicalPartition(LinuxPartition, partition.LogicalPartition):
    # pylint: disable=W0223
    # The methods below are overriden by platform-specific implementations
    pass

class LinuxGUIDPartition(LinuxPartition, partition.GUIDPartition):
    # pylint: disable=W0223
    # The methods below are overriden by platform-specific implementations
    pass

class LinuxPartitionTable(object):
    def __init__(self, disk_drive):
        super(LinuxPartitionTable, self).__init__()
        self._disk_drive = disk_drive

    def _translate_partition_object(self, parted_partition):
        from infi.parted import GUIDPartition
        if isinstance(parted_partition, GUIDPartition):
            return LinuxGUIDPartition(self._disk_drive, parted_partition)
        if parted_partition.get_type() == "Primary":
            return LinuxPrimaryPartition(self._disk_drive, parted_partition)
        if parted_partition.get_type() == "Extended":
            return LinuxExtendedPartition(self._disk_drive, parted_partition)
        if parted_partition.get_type() == "Logical":
            return LinuxLogicalPartition(self._disk_drive, parted_partition)
        # If there is only primary, then the type is empty
        return LinuxPrimaryPartition(self._disk_drive, parted_partition)

    @cached_method
    def get_partitions(self):
        parted_disk = self._disk_drive._get_parted_disk_drive()
        return [self._translate_partition_object(parted_partition)
                for parted_partition in parted_disk.get_partitions()]

    @cached_method
    def get_disk_drive(self):
        return self._disk_drive

    def create_partition_for_whole_table(self, file_system_object, alignment_in_bytes=None):
        self._disk_drive._get_parted_disk_drive().create_partition_for_whole_drive(file_system_object.get_name(), alignment_in_bytes)
        clear_cache(self)
        return self.get_partitions()[0]

class LinuxMBRPartitionTable(LinuxPartitionTable, partition.MBRPartitionTable):
    @classmethod
    def create_partition_table(cls, disk_drive, alignment_in_bytes=None):
        disk_drive._get_parted_disk_drive().create_a_new_partition_table("msdos", alignment_in_bytes)
        return cls(disk_drive)

class LinuxGUIDPartitionTable(LinuxPartitionTable, partition.GUIDPartitionTable):
    @classmethod
    def create_partition_table(cls, disk_drive, alignment_in_bytes=None):
        disk_drive._get_parted_disk_drive().create_a_new_partition_table("gpt", alignment_in_bytes)
        return cls(disk_drive)
