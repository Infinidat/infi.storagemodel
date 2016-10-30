from infi.pyutils.lazy import cached_method
from ..base import disk, gevent_wrapper

# pylint: disable=W0212,E1002

from infi.diskmanagement import Disk

class WindowsDiskDrive(disk.DiskDrive):
    def __init__(self, storage_device, path):
        super(WindowsDiskDrive, self).__init__()
        self._storage_device = storage_device
        self._disk_object = Disk(self._storage_device.get_physical_drive_number())
        self._path = path

    @cached_method
    def get_storage_device(self):
        return self._storage_device

    @cached_method
    def get_block_access_path(self):
        return self._disk_object._path

    def is_empty(self):
        return len(gevent_wrapper.defer(self._disk_object.get_partitions)()) == 0

    def get_partition_table(self):
        from .partition import WindowsMBRPartitionTable, WindowsGUIDPartitionTable
        if gevent_wrapper.defer(self._disk_object.is_gpt)():
            return WindowsGUIDPartitionTable(self)
        return WindowsMBRPartitionTable(self)

    def delete_partition_table(self):
        gevent_wrapper.defer(self._disk_object.destroy_partition_table)()

    def create_mbr_partition_table(self, alignment_in_bytes=None):
        from .partition import WindowsMBRPartitionTable
        return WindowsMBRPartitionTable.create_partition_table(self, alignment_in_bytes)

    def create_guid_partition_table(self, alignment_in_bytes=None):
        from .partition import WindowsGUIDPartitionTable
        return WindowsGUIDPartitionTable.create_partition_table(self, alignment_in_bytes)

    def is_online(self):
        return gevent_wrapper.defer(self._disk_object.is_online)()

    def online(self):
        return gevent_wrapper.defer(self._disk_object.online)()

    def offline(self):
        return gevent_wrapper.defer(self._disk_object.offline)()

    def has_read_only_attribute(self):
        return gevent_wrapper.defer(self._disk_object.is_read_only)()

    def unset_read_only_attribute(self):
        gevent_wrapper.defer(self._disk_object.read_write)()

    def set_read_only_attribute(self):
        gevent_wrapper.defer(self._disk_object.read_only)()

    @cached_method
    def get_block_access_paths_for_partitions(self):
        from infi.wioctl.errors import WindowsException
        try:
            return super(WindowsDiskDrive, self).get_block_access_paths_for_partitions()
        except WindowsException:
            return []


class WindowsDiskModel(disk.DiskModel):
    def find_disk_drive_by_block_access_path(self, path):
        from infi.storagemodel import get_storage_model
        scsi = get_storage_model().get_scsi()
        multipath = get_storage_model().get_native_multipath()
        all_devices = scsi.get_all_scsi_block_devices() + multipath.get_all_multipath_block_devices()
        storage_device = [device for device in all_devices if device.get_block_access_path() == path][0]
        return WindowsDiskDrive(storage_device, path)

# TODO
# mount manager
# mount repository
