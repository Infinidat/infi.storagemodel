import unittest

class ExamplesTestCase(unittest.TestCase):
    def test_devlist_runs(self):
        from . import devlist
        devlist()
