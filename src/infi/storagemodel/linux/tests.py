
import unittest
import mock

from . import LinuxStorageModel

class InitiateRescan(unittest.TestCase):

    def test_for_real(self):
        from . import is_rescan_script_exists
        if not is_rescan_script_exists():
            raise unittest.SkipTest
        model = LinuxStorageModel()
        model.initiate_rescan()

    def test__no_script_found(self):
        from ..errors import StorageModelError
        model = LinuxStorageModel()
        original_call_function = model._call_rescan_script

        def side_effect(*args, **kwargs):
            return original_call_function(dict())

        with mock.patch_object(LinuxStorageModel, "_call_rescan_script") as patch:
            model = LinuxStorageModel()
            patch.side_effect = side_effect
            self.assertIsInstance(model._call_rescan_script, mock.Mock)
            self.assertRaises(StorageModelError, model.initiate_rescan)
            self.assertTrue(patch.called)
