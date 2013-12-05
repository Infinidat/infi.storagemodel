
from infi.pyutils.lazy import cached_method
from ..base import partition
from .filesystem import WindowsFileSystem

# pylint: disable=W0212,E1002

class WindowsPartitionTable(object):
    def __init__(self, disk_device):
        super(WindowsPartitionTable, self).__init__()
        self._disk_device = disk_device

    def _create_partition_table(self, style, alignment_in_bytes=None):
        return self._disk_device._disk_object.create_partition_table(style, alignment_in_bytes)

    def _get_partitions(self):
        return self._disk_device._disk_object.get_partitions()

    def get_disk_drive(self):
        return self._disk_device

    def create_partition_for_whole_table(self, file_system_object, alignment_in_bytes=None):
        self._disk_device._disk_object.create_first_partition(alignment_in_bytes)
        return self.get_partitions()[0]

class WindowsGPTPartitionTable(WindowsPartitionTable, partition.GPTPartitionTable):
    @classmethod
    def create_partition_table(cls, disk_drive, alignment_in_bytes=None):
        obj = cls(disk_drive)
        obj._create_partition_table('gpt', alignment_in_bytes)
        return cls(disk_drive)

    def get_partitions(self):
        return [WindowsGUIDPartition(self, partition) for partition in self._get_partitions()]

class WindowsMBRPartitionTable(WindowsPartitionTable, partition.GPTPartitionTable):
    @classmethod
    def create_partition_table(cls, disk_drive, alignment_in_bytes=None):
        obj = cls(disk_drive)
        obj._create_partition_table('mbr', alignment_in_bytes)
        return cls(disk_drive)

    def get_partitions(self):
        return [WindowsPrimaryPartition(self, partition) for partition in self._get_partitions()[:3]] + \
               [WindowsLogicalPartition(self, partition) for partition in self._get_partitions()[3:]]

class WindowsPartition(object):
    def __init__(self, disk_device, partition_object):
        super(WindowsPartition, self).__init__()
        self._disk_device = disk_device
        self._partition_object = partition_object

    def get_size_in_bytes(self):
        return self._partition_object.get_size_in_bytes()

    @cached_method
    def _get_volume(self):
        return self._partition_object.get_volume()

    @cached_method
    def get_block_access_path(self):
        volume = self._get_volume()
        if volume is None:
            return None
        return volume.get_volume_guid()

    def get_containing_disk(self):
        return self._disk_device

    def get_current_filesystem(self): # pragma: no cover
        return WindowsFileSystem("NTFS")

    def resize(self, size_in_bytes):
        self._partition_object.resize(size_in_bytes)

class WindowsPrimaryPartition(WindowsPartition, partition.PrimaryPartition):
    pass

class WindowsLogicalPartition(WindowsPartition, partition.LogicalPartition):
    pass

class WindowsGUIDPartition(WindowsPartition, partition.GUIDPartition):
    pass
