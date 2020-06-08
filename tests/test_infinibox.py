from infi import unittest

from infi.storagemodel.vendor.infinidat.infinibox import connectivity


class InfiniBoxConnectivityTestCase(unittest.TestCase):

    def test_get_system_serial_from_iqn(self):
        # InfiniBox v5.5+
        self.assertEqual(connectivity.get_system_serial_from_iqn('iqn.2009-11.com.infinidat:storage:infinibox-sn-2812'), 2812)
        # InfiniBox before v5.5
        self.assertEqual(connectivity.get_system_serial_from_iqn('iqn.2009-11.com.infinidat:storage:infinibox-sn-2812-1234'), 2812)
        # Messed up IQN from infinisim - INFRADEV-13513
        self.assertEqual(connectivity.get_system_serial_from_iqn('iqn.2009-11.com.infinidat:storage:infinibox-sn-<machine_serial_number>-2812-1234'), 2812)
        self.assertEqual(connectivity.get_system_serial_from_iqn('iqn.2009-11.com.infinidat:storage:infinibox-sn-<machine_serial_number>-2812'), 2812)
        # Non-InfiniBox
        with self.assertRaises(connectivity.InvalidInfiniboxConnectivity):
            connectivity.get_system_serial_from_iqn('foo.bar')
        with self.assertRaises(connectivity.InvalidInfiniboxConnectivity):
            connectivity.get_system_serial_from_iqn('iqn.1991-05.com.microsoft:example')
        with self.assertRaises(connectivity.InvalidInfiniboxConnectivity):
            connectivity.get_system_serial_from_iqn('iqn.1998-01.com.vmware.iscsi:name999')

    def test_get_system_serial_from_wwn(self):
        self.assertEqual(connectivity.get_system_serial_from_wwn('57:42:B0:F0:00:04:12:15'), 1042)
        self.assertEqual(connectivity.get_system_serial_from_wwn('5742B0F000041215'), 1042)
        # Non-InfiniBox
        with self.assertRaises(connectivity.InvalidInfiniboxConnectivity):
            connectivity.get_system_serial_from_wwn('500277a4100c4e21')

