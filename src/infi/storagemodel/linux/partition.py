from infi.pyutils.lazy import cached_method
from ..base import partition

class LinuxPartition(partition.Partition):
    def __init__(self, containing_disk, parted_partition):
        super(LinuxPartition, self).__init__()
        self._parted_partition = parted_partition
        self._containing_disk = containing_disk

    @cached_method
    def get_size_in_bytes(self):
        return self._parted_partition.get_size().bits / 8

    @cached_method
    def get_block_access_path(self):
        return self._parted_partition.get_access_path()

    @cached_method
    def get_containing_disk(self):
        return self._containing_disk

    @cached_method
    def get_current_filesystem(self):
        raise NotImplementedError()

class LinuxPrimaryPartition(LinuxPartition, partition.PrimaryPartition):
    pass

class LinuxExtendedPartition(LinuxPartition, partition.ExtendedPartition):
    pass

class LinuxLogicalPartition(LinuxPartition, partition.LogicalPartition):
    pass

class LinuxGUIDPartition(LinuxPartition, partition.GUIDPartition):
    pass

class LinuxPartitionTable(object):
    def __init__(self, disk_drive):
        super(LinuxPartitionTable, self).__init__()
        self._disk_drive = disk_drive

    def _translate_partition_object(self, parted_partition):
        if isinstance(parted_partition, LinuxGUIDPartition):
            return LinuxGUIDPartition(self._disk_drive, parted_partition)
        if parted_partition.get_type() == "Primary":
            return LinuxPrimaryPartition(self._disk_drive, parted_partition)
        if parted_partition.get_type() == "Extended":
            return LinuxExtendedPartition(self._disk_drive, parted_partition)
        if parted_partition.get_type() == "Logical":
            return LinuxLogicalPartition(self._disk_drive, parted_partition)

    @cached_method
    def get_partitions(self):
        parted_disk = self._disk_drive._get_parted_disk_drive()
        return [self._translate_partition_object(parted_partition)
                for parted_partition in parted_disk.get_partitions()]

    @cached_method
    def get_disk_drive(self):
        return self._disk_drive

    def create_partition_for_whole_table(self, file_system_object):
        self._disk_drive._get_parted_disk_drive().create_partition_for_whole_drive(file_system_object.get_name())

class LinuxMBRPartitionTable(LinuxPartitionTable, partition.MBRPartitionTable):
    @classmethod
    def create_partition_table(cls, disk_drive):
        disk_drive._get_parted_disk_drive().create_a_new_partition_table("msdos")
        return cls(disk_drive)

class LinuxGPTPartitionTable(LinuxPartitionTable, partition.GPTPartitionTable):
    @classmethod
    def create_partition_table(cls, disk_drive):
        disk_drive._get_parted_disk_drive().create_a_new_partition_table("gpt")
        return cls(disk_drive)
