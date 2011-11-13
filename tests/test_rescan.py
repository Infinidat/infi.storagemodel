import unittest

class TestModel(unittest.TestCase):
    def setUp(self):
        from infi.storagemodel import get_storage_model
        try:
            _ = get_storage_model()
        except ImportError:
            raise unittest.SkipTest("Unsupported Platform")

    def test_rescan__nothing(self):
        from infi.storagemodel import get_storage_model
        get_storage_model().rescan_and_wait_for()

    def test_rescan__timeout(self):
        from infi.storagemodel import get_storage_model
        from infi.storagemodel.errors import TimeoutError
        from infi.storagemodel.predicates import DiskExists
        self.assertRaises(TimeoutError, get_storage_model().rescan_and_wait_for, *(DiskExists("fooBar"), 1))

    def test_cached_methods(self):
        raise unittest.SkipTest("Skipping this test because _create_disk_model is not implemented on Windows and Linux for now")
        from infi.pyutils.lazy import populate_cache
        from infi.storagemodel import get_storage_model
        model = get_storage_model()
        scsi = model.get_scsi()
        native_multipath = model.get_native_multipath()
        devices = scsi.get_all_scsi_block_devices() + native_multipath.get_all_multipath_devices()
        for device in devices:
            populate_cache(device)
