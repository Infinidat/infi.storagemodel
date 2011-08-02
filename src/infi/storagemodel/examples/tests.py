import unittest

class ExamplesTestCae(unittest.TestCase):
    def test_devlist_runs(self):
        from . import devlist
        _ = devlist()
