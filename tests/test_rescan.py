import unittest

class TestModel(unittest.TestCase):
    def test_rescan__nothing(self):
        from infi.storagemodel import get_storage_model
        get_storage_model().rescan_and_wait_for()

    def test_rescan__timeout(self):
        from infi.storagemodel import get_storage_model
        from infi.storagemodel.base import TimeoutError
        from infi.storagemodel.predicates import DiskExists
        self.assertRaises(TimeoutError, get_storage_model().rescan_and_wait_for, *(DiskExists("fooBar"), 1))
