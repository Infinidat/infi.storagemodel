
from infi import unittest
import mock
from contextlib import contextmanager, nested

class ModelTestCase(unittest.TestCase):
    def setUp(self):
        from os import name
        if name != "nt":
            raise unittest.SkipTest

    def _get_model(self):
        from . import WindowsStorageModel
        model = WindowsStorageModel()
        return model

    def test_create_model(self):
        model = self._get_model()
        scsi = model.scsi
        native_multipath = model.native_multipath

    def _assert_block_device(self, device):
        from ..dtypes import HCTL
        self.assertGreater(device.size_in_bytes, 0)
        self.assertIsInstance(device.hctl, HCTL)
        self.assertTrue(device.display_name.startswith("PHYSICALDRIVE"))
        self.assertIsInstance(device.block_access_path, unicode)
        self.assertIsInstance(device.scsi_access_path, unicode)
        self.assertIsInstance(device.scsi_vendor_id, str)
        self.assertIsInstance(device.scsi_product_id, str)
        self.assertEqual(device.scsi_vid_pid, (device.scsi_vendor_id, device.scsi_product_id))
        _ = device.scsi_inquiry_pages
        self.assertIsInstance(device.scsi_serial_number, str)
        _ = device.scsi_standard_inquiry
        self._assert_connectivity(device)

    def test_get_block_devices(self):
        model = self._get_model()
        block_devices = model.scsi.get_all_scsi_block_devices()
        for device in block_devices:
            self._assert_block_device(device)
        return block_devices

    def test_get_multipath_devices(self):
        model = self._get_model()
        multipath_devices = model.native_multipath.get_all_multipath_devices()
        for device in multipath_devices:
            self._assert_multipath_device(device)
        return multipath_devices

    def _assert_connectivity(self, item):
        from ..connectivity import LocalConnectivity, FCConnectivity
        connectivity = item.connectivity
        if isinstance(connectivity, LocalConnectivity):
            return
        _ = connectivity.initiator_wwn
        _ = connectivity.target_wwn

    def _assert_multipath_device(self, device):
        self.assertGreater(device.size_in_bytes, 0)
        self.assertTrue(device.display_name.startswith("PHYSICALDRIVE"))
        self.assertIsInstance(device.device_access_path, unicode)
        self.assertIsInstance(device.scsi_vendor_id, str)
        self.assertIsInstance(device.scsi_product_id, str)
        self.assertEqual(device.scsi_vid_pid, (device.scsi_vendor_id, device.scsi_product_id))
        _ = device.scsi_inquiry_pages
        self.assertIsInstance(device.scsi_serial_number, str)
        _ = device.scsi_standard_inquiry
        from ..dtypes import HCTL
        for path in device.paths:
            self.assertIsInstance(path.hctl, HCTL)
            self._assert_connectivity(path)
            _ = path.state
        _ = device.policy

class MockModelTestCase(ModelTestCase):
    def setUp(self):
        pass

    def test_get_block_devices(self):
        with nested(mock.patch("infi.devicemanager.DeviceManager"),
                    mock.patch("infi.devicemanager.Device"),
                    mock.patch("infi.storagemodel.windows.WindowsSCSIBlockDevice"),
                    ) as (DeviceManager, Device, WindowsSCSIBlockDevice):
            Device.return_value.psuedo_device_object = r'\Device\00000000'
            Device.return_value.ioctl_interface = mock.Mock()
            WindowsSCSIBlockDevice.return_value.ioctl_interface.storage_get_device_number.return_value = 1
            DeviceManager.return_value.disk_drives = [Device()]
            block_devices = super(MockModelTestCase, self).test_get_block_devices()
            self.assertEqual(len(block_devices), 1)

    def test_get_multipath_devices(self):
        class MultipathDeviceMock(object):
            pass

        with nested(mock.patch("infi.wmpio.WmiClient"),
                    mock.patch("infi.devicemanager.DeviceManager"),
                    mock.patch("infi.devicemanager.Device"),
                    mock.patch("infi.wmpio.get_multipath_devices"),
                    ) as (WmiClient, DeviceManager, Device, get_multipath_devices):
            DeviceManager.return_value.disk_drives = [Device()]
            get_multipath_devices.return_value = dict(someId=MultipathDeviceMock())
            multipath_devices = ModelTestCase.test_get_multipath_devices(self)
            self.assertEqual(len(multipath_devices), 0)

    def _assert_block_device(self, device):
        pass
