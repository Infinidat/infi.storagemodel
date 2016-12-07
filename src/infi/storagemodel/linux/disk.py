from ..base import disk
from infi.pyutils.lazy import cached_method

# pylint: disable=R0921

class LinuxDiskDrive(disk.DiskDrive):
    def __init__(self, storage_device, scsi_disk_path):
        super(LinuxDiskDrive, self).__init__()
        self._storage_device = storage_device
        self._scsi_disk_path = scsi_disk_path

    def _get_parted_disk_drive(self):
        from infi.parted import Disk
        return Disk(self._scsi_disk_path)

    @cached_method
    def get_storage_device(self):
        return self._storage_device

    @cached_method
    def get_block_access_path(self):
        return self._scsi_disk_path

    @cached_method
    def get_partition_table(self):
        from .partition import LinuxGUIDPartitionTable, LinuxMBRPartitionTable
        parted = self._get_parted_disk_drive()
        if not parted.has_partition_table():
            raise disk.NoPartitionTable()
        if parted.get_partition_table_type() == "gpt":
            return LinuxGUIDPartitionTable(self)
        elif parted.get_partition_table_type() == "msdos":
            return LinuxMBRPartitionTable(self)
        raise disk.NoPartitionTable()

    def is_empty(self):
        return not self._get_parted_disk_drive().has_partition_table()

    def delete_partition_table(self):
        raise NotImplementedError()

    def create_guid_partition_table(self, alignment_in_bytes=None):
        from .partition import LinuxGUIDPartitionTable
        return LinuxGUIDPartitionTable.create_partition_table(self, alignment_in_bytes)

    def create_mbr_partition_table(self, alignment_in_bytes=None):
        from .partition import LinuxMBRPartitionTable
        return LinuxMBRPartitionTable.create_partition_table(self, alignment_in_bytes)

    def _format_partition(self, number, filesystem_name, **kwargs):
        self._get_parted_disk_drive().format_partition(number, filesystem_name, **kwargs)

    @cached_method
    def get_block_access_paths_for_partitions(self):
        from glob import glob
        if self._scsi_disk_path[-1].isalpha():
            # disk path is like 'sda' or 'mpathc'
            glob_patterns = ['%s_part[0-9]*',   # e.g. SuSE 12
                             '%s-part[0-9]*',   # e.g. SuSE 12
                             '%sp[0-9]*',       # e.g. CentOS 6
                             '%s[0-9]*']        # e.g. CentOS/RHEL/Oracle 7
        else:
            # disk path is like 'mpath3'
            glob_patterns = ['%s-part[0-9]*',   # e.g. Ubuntu-14.04
                             '%sp[0-9]*']       # e.g. Ubuntu-14.04
        res = []
        for glob_pattern in glob_patterns:
            res.extend([item for item in glob(glob_pattern % self._scsi_disk_path)])
        return res


class LinuxDiskModel(disk.DiskModel):
    def find_disk_drive_by_block_access_path(self, path):
        from infi.storagemodel import get_storage_model
        scsi = get_storage_model().get_scsi()
        multipath = get_storage_model().get_native_multipath()
        all_devices = scsi.get_all_scsi_block_devices() + multipath.get_all_multipath_block_devices()
        storage_device = [device for device in all_devices
                          if device.get_block_access_path() == path][0]
        return LinuxDiskDrive(storage_device, path)
