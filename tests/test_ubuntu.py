from unittest import SkipTest
from infi import unittest

class UbuntuTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super(UbuntuTestCase, cls).setUpClass()
        if not cls._is_ubuntu():
            raise SkipTest("Can only run on ubuntu")
        if not cls._is_root():
            raise SkipTest("Can only run under root")

    @classmethod
    def _is_ubuntu(cls):
        import distro
        return distro.id() == "ubuntu"

    @classmethod
    def _is_root(cls):
        from os import getuid
        return getuid() == 0

    def test_get_sda(self):
        from infi.storagemodel import get_storage_model
        model = get_storage_model()
        block_devices = model.get_scsi().get_all_scsi_block_devices()
        disk = block_devices[0].get_disk_drive()
        self.assertFalse(disk.is_empty())
        partition_table = disk.get_partition_table()
        self.assertGreaterEqual(len(partition_table.get_partitions()), 1)
        size = disk.get_size_in_bytes()
