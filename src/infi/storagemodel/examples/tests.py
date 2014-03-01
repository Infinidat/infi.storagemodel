import unittest

# pylint: disable=R0904

class ExamplesTestCase(unittest.TestCase):
    def setUp(self):
        from .. import get_storage_model
        try:
            get_storage_model()
        except ImportError:
            raise unittest.SkipTest()

    def test_devlist_runs(self):
        from . import devlist
        devlist()
