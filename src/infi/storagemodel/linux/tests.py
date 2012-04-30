
import unittest
import mock

from . import LinuxStorageModel

# pylint: disable=W0312,W0212,W0710,R0904

class InitiateRescan(unittest.TestCase):

    def test_for_real(self):
        model = LinuxStorageModel()
        model.initiate_rescan()
