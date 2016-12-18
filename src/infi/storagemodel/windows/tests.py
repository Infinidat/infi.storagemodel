
import unittest
import mock
import six

try:
    from contextlib import ExitStack
except ImportError:
    from contextlib2 import ExitStack

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
        model.get_scsi()
        model.get_native_multipath()

    def _assert_block_device(self, device):
        log.debug("asserting on device %s", device.get_display_name())
        from infi.dtypes.hctl import HCTL
        self.assertGreater(device.get_size_in_bytes(), 0)
        self.assertIsInstance(device.get_hctl(), HCTL)
        self.assertTrue(device.get_display_name().startswith("PHYSICALDRIVE"))
        self.assertIsInstance(device.get_block_access_path(), six.string_types)
        self.assertIsInstance(device.get_scsi_access_path(), six.string_types)
        self.assertIsInstance(device.get_scsi_vendor_id(), six.string_types)
        self.assertIsInstance(device.get_scsi_product_id(), six.string_types)
        self.assertEqual(device.get_scsi_vid_pid(), (device.get_scsi_vendor_id(), device.get_scsi_product_id()))
        device.get_scsi_inquiry_pages()
        self.assertIsInstance(device.get_scsi_serial_number(), six.string_types)
        device.get_scsi_standard_inquiry()
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
        from ..connectivity import LocalConnectivity
        connectivity = item.get_connectivity()
        if isinstance(connectivity, LocalConnectivity):
            return
        connectivity.get_initiator_wwn()
        connectivity.get_target_wwn()

    def _assert_multipath_device(self, device):
        self.assertGreater(device.get_size_in_bytes(), 0)
        self.assertTrue(device.get_display_name().startswith("PHYSICALDRIVE"))
        self.assertIsInstance(device.get_block_access_path(), six.string_types)
        self.assertIsInstance(device.get_scsi_vendor_id(), six.string_types)
        self.assertIsInstance(device.get_scsi_product_id(), six.string_types)
        self.assertEqual(device.get_scsi_vid_pid(), (device.get_scsi_vendor_id(), device.get_scsi_product_id()))
        device.get_scsi_inquiry_pages()
        self.assertIsInstance(device.get_scsi_serial_number(), six.string_types)
        device.get_scsi_standard_inquiry()
        from infi.dtypes.hctl import HCTL
        for path in device.get_paths():
            self.assertIsInstance(path.get_hctl(), HCTL)
            self._assert_connectivity(path)
            path.get_state()
        device.get_policy

    def test_find_devices(self):
        model = self._get_model()
        scsi = model.get_scsi()
        devices = scsi.get_all_scsi_block_devices()
        self.assertRaises(KeyError, scsi.find_scsi_block_device_by_block_access_path, "foo")
        scsi.find_scsi_block_device_by_block_access_path(devices[0].get_block_access_path())
        self.assertRaises(KeyError, scsi.find_scsi_block_device_by_scsi_access_path, "foo")
        scsi.find_scsi_block_device_by_scsi_access_path(devices[0].get_scsi_access_path())
        self.assertRaises(KeyError, scsi.find_scsi_block_device_by_hctl, "foo")
        scsi.find_scsi_block_device_by_hctl(devices[0].get_hctl())

class MockModelTestCase(ModelTestCase):
    def setUp(self):
        pass

    def test_get_block_devices(self):
        with ExitStack() as stack:
            DeviceManager, Device, WindowsSCSIBlockDevice = [
                stack.enter_context(c) for c in [
                    mock.patch("infi.devicemanager.DeviceManager"),
                    mock.patch("infi.devicemanager.Device"),
                    mock.patch("infi.storagemodel.windows.scsi.WindowsSCSIBlockDevice")
                ]
            ]

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

        with ExitStack() as stack:
            _, DeviceManager, Device, get_multipath_devices = [
                stack.enter_context(c) for c in [
                    mock.patch("infi.wmpio.WmiClient"),
                    mock.patch("infi.devicemanager.DeviceManager"),
                    mock.patch("infi.devicemanager.Device"),
                    mock.patch("infi.wmpio.get_multipath_devices")
                ]
            ]

            DeviceManager.return_value.disk_drives = [Device()]
            get_multipath_devices.return_value = dict(someId=MultipathDeviceMock())
            multipath_devices = ModelTestCase.test_get_multipath_devices(self)
            self.assertEqual(len(multipath_devices), 0)

    def _assert_block_device(self, device):
        pass

    def test_find_devices(self):
        pass

    def _raise(self, exception_class=KeyError):
        raise exception_class()

    def test_is_disk_visible_in_device_manager(self):
        from .device_helpers import is_disk_visible_in_device_manager
        from munch import Munch
        self.assertTrue(is_disk_visible_in_device_manager(Munch(is_hidden=lambda: False)))
        self.assertFalse(is_disk_visible_in_device_manager(Munch(is_hidden=lambda: True)))
        self.assertFalse(is_disk_visible_in_device_manager(Munch(is_hidden=lambda: self._raise())))

    def test_private_iter_failures(self):
        from .scsi import WindowsSCSIModel
        from .device_helpers import MPIO_BUS_DRIVER_INSTANCE_ID
        from munch import Munch

        def _build(managed_by_mpio, visible):
            return Munch(parent=Munch(_instance_id=Munch(lower=lambda: MPIO_BUS_DRIVER_INSTANCE_ID if managed_by_mpio else self._raise())),
                         is_hidden=lambda: False if visible else self._raise())

        device_manager = Munch(disk_drives=[])
        for managed_by_mpio in (True, False):
            device_manager.disk_drives.append(_build(managed_by_mpio, False))

        class MockWindowsSCSIModel(WindowsSCSIModel):
            def get_device_manager(self):
                return device_manager

        model = MockWindowsSCSIModel()
        devices = list(model._iter())
        self.assertEqual(len(devices), 0)
