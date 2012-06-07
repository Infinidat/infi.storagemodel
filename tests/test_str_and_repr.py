from infi import unittest
from infi.storagemodel import get_storage_model

class ReprTestCase(unittest.TestCase):
    def setUp(self):
        self.model = get_storage_model()
        self.scsi = self.model.get_scsi()
    
    def test_repr(self):
        items = [repr(item) for item in self.scsi.get_all_scsi_block_devices()]
        items = [repr(item) for item in self.scsi.get_all_storage_controller_devices()]

    def test_str(self):
        items = [repr(item) for item in self.scsi.get_all_scsi_block_devices()]
        items = [repr(item) for item in self.scsi.get_all_storage_controller_devices()]

