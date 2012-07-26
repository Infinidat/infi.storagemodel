
import unittest
import mock
from contextlib import nested

from logging import getLogger
log = getLogger(__name__)

# pylint: disable=R0904,C0103,R0922

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
        scsi = model.get_scsi()
        native_multipath = model.get_native_multipath()

    def _assert_block_device(self, device):
        log.debug("asserting on device %s", device.get_display_name())
        from infi.dtypes.hctl import HCTL
        self.assertGreater(device.get_size_in_bytes(), 0)
        self.assertIsInstance(device.get_hctl(), HCTL)
        self.assertTrue(device.get_display_name().startswith("PHYSICALDRIVE"))
        self.assertIsInstance(device.get_block_access_path(), unicode)
        self.assertIsInstance(device.get_scsi_access_path(), unicode)
        self.assertIsInstance(device.get_scsi_vendor_id(), str)
        self.assertIsInstance(device.get_scsi_product_id(), str)
        self.assertEqual(device.get_scsi_vid_pid(), (device.get_scsi_vendor_id(), device.get_scsi_product_id()))
        _ = device.get_scsi_inquiry_pages()
        self.assertIsInstance(device.get_scsi_serial_number(), str)
        _ = device.get_scsi_standard_inquiry()
        self._assert_connectivity(device)

    def test_get_block_devices(self):
        model = self._get_model()
        block_devices = model.get_scsi().get_all_scsi_block_devices()
        for device in block_devices:
            self._assert_block_device(device)
        return block_devices

    def test_get_multipath_devices(self):
        model = self._get_model()
        multipath_devices = model.get_native_multipath().get_all_multipath_block_devices()
        for device in multipath_devices:
            self._assert_multipath_device(device)
        return multipath_devices

    def _assert_connectivity(self, item):
        from ..connectivity import LocalConnectivity, FCConnectivity
        connectivity = item.get_connectivity()
        if isinstance(connectivity, LocalConnectivity):
            return
        _ = connectivity.get_initiator_wwn()
        _ = connectivity.get_target_wwn()

    def _assert_multipath_device(self, device):
        self.assertGreater(device.get_size_in_bytes(), 0)
        self.assertTrue(device.get_display_name().startswith("PHYSICALDRIVE"))
        self.assertIsInstance(device.get_block_access_path(), unicode)
        self.assertIsInstance(device.get_scsi_vendor_id(), str)
        self.assertIsInstance(device.get_scsi_product_id(), str)
        self.assertEqual(device.get_scsi_vid_pid(), (device.get_scsi_vendor_id(), device.get_scsi_product_id()))
        _ = device.get_scsi_inquiry_pages()
        self.assertIsInstance(device.get_scsi_serial_number(), str)
        _ = device.get_scsi_standard_inquiry()
        from infi.dtypes.hctl import HCTL
        for path in device.get_paths():
            self.assertIsInstance(path.get_hctl(), HCTL)
            self._assert_connectivity(path)
            _ = path.get_state()
        _ = device.get_policy

    def test_find_devices(self):
        model = self._get_model()
        scsi = model.get_scsi()
        devices = scsi.get_all_scsi_block_devices()
        self.assertRaises(KeyError, scsi.find_scsi_block_device_by_block_access_path, "foo")
        _ = scsi.find_scsi_block_device_by_block_access_path(devices[0].get_block_access_path())
        self.assertRaises(KeyError, scsi.find_scsi_block_device_by_scsi_access_path, "foo")
        _ = scsi.find_scsi_block_device_by_scsi_access_path(devices[0].get_scsi_access_path())
        self.assertRaises(KeyError, scsi.find_scsi_block_device_by_hctl, "foo")
        _ = scsi.find_scsi_block_device_by_hctl(devices[0].get_hctl())

class MockModelTestCase(ModelTestCase):
    def setUp(self):
        pass

    def test_get_block_devices(self):
        with nested(mock.patch("infi.devicemanager.DeviceManager"),
                    mock.patch("infi.devicemanager.Device"),
                    mock.patch("infi.storagemodel.windows.scsi.WindowsSCSIBlockDevice"),
                    ) as (DeviceManager, Device, WindowsSCSIBlockDevice):
            Device.return_value.psuedo_device_object = r'\Device\00000000'
            Device.return_value.get_ioctl_interface = mock.Mock()
            Device.return_value.is_hidden.return_value = False
            WindowsSCSIBlockDevice.return_value.get_ioctl_interface.storage_get_device_number.return_value = 1
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

    def test_find_devices(self):
        pass
