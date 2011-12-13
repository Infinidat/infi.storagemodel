
import unittest
import mock

from . import LinuxStorageModel

# pylint: disable=W0312,W0212,W0710,R0904

class InitiateRescan(unittest.TestCase):

    def test_for_real(self):
        from . import is_rescan_script_exists
        if not is_rescan_script_exists():
            raise unittest.SkipTest
        model = LinuxStorageModel()
        model.initiate_rescan()

    def test__no_script_found(self):
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
