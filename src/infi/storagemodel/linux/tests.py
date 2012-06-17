
import unittest
import mock

from infi.storagemodel import get_platform_name

# pylint: disable=W0312,W0212,W0710,R0904

class InitiateRescan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if get_platform_name() != 'linux':
            raise unittest.SkipTest("This tests runs only on Linux")

    def test_for_real(self):
        from . import LinuxStorageModel
        from . import is_rescan_script_exists
        if not is_rescan_script_exists():
            raise unittest.SkipTest
        model = LinuxStorageModel()
        model.initiate_rescan()

    def test__no_script_found(self):
        from . import LinuxStorageModel
        from ..errors import StorageModelError
        from .. import linux

        original_call_function = linux._call_rescan_script

        def side_effect(*args, **kwargs):
            raise StorageModelError

        with mock.patch("infi.storagemodel.linux._call_rescan_script") as patch:
            model = LinuxStorageModel()
            patch.side_effect = side_effect
            self.assertRaises(StorageModelError, model.initiate_rescan)
            self.assertTrue(patch.called)

class RescanScript(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if get_platform_name() == 'windows':
            raise unittest.SkipTest("This test does not run on Windows because there is no fork!")

    def test_locate(self):
        from . import _locate_rescan_script
        script = _locate_rescan_script()
        self.assertIsInstance(script, str)

    def test_call__sync(self):
        with mock.patch("infi.storagemodel.linux._get_all_host_bus_adapter_numbers") as get_hbas:
            get_hbas.return_value = [3,4,5]
            with mock.patch("infi.execute.execute") as execute:
                from . import _call_rescan_script
                _call_rescan_script(sync=True)
                self.assertTrue(execute.called)
                self.assertEqual(execute.call_count, 1)

    def test_call__async(self):
        with mock.patch("os.fork"), mock.patch("os._exit"), mock.patch("daemon.basic_daemonize"), mock.patch("infi.execute.execute") as execute:
            from . import _call_rescan_script
            _call_rescan_script(sync=True)
            self.assertTrue(execute.called)
            self.assertEqual(execute.call_count, 1)

