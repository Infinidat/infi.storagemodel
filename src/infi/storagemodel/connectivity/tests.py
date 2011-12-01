from unittest import TestCase

from . import FCConnectivity, LocalConnectivity

SRC = "0x0102030405060708"
DST = "0x0203040506070809"

# pylint: disable=R0904

class TestEquality(TestCase):
    def test_mixed_types(self):
        a = FCConnectivity(None, SRC, SRC)
        b = LocalConnectivity()
        self.assertNotEqual(a, b)

    def test_same_types_fc__not_identical(self):
        a = FCConnectivity(None, SRC, SRC)
        b = FCConnectivity(None, SRC, DST)
        self.assertNotEqual(a, b)

    def test_same_types_fc__identical(self):
        a = FCConnectivity(None, SRC, SRC)
        b = FCConnectivity(None, SRC, SRC)
        self.assertEqual(a, b)
