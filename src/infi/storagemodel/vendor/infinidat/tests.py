import unittest
from infi.storagemodel.vendor.infinidat.infinibox import wwn


class InfiniBoxWWN_TestCase(unittest.TestCase):
    def test_box_ci10(self):
        item = wwn.InfinidatWWN("57:42:b0:f0:00:75:7f:11")
        self.assertEqual(item.get_system_serial(), 30079)
        self.assertEqual(item.get_node_id(), 1)
        self.assertEqual(item.get_port_id(), 1)
        with self.assertRaises(KeyError):
            item.get_soft_target_id()

    def test_ibox053(self):
        item = wwn.InfinidatWWN("20:01:74:2B:0F:00:04:1D")
        self.assertEqual(item.get_system_serial(), 1053)
        self.assertEqual(item.get_soft_target_id(), 1)
        with self.assertRaises(KeyError):
            item.get_node_id()

    def test_invalid_wwn(self):
        with self.assertRaises(wwn.InvalidInfinidatWWN):
            wwn.InfinidatWWN("20:01:71:2B:0F:00:04:1D")
