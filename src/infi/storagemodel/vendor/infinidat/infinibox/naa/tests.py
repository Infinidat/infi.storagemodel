from unittest import TestCase
from . import InfinidatNAA
from .. import NFINIDAT_IEEE
from binascii import unhexlify

TEST_NAA = "6742b0f000004e2b000000000000018c"

class InfinidatNAATest(TestCase):
    def test_string_param(self):
        naa = InfinidatNAA(unhexlify(TEST_NAA))
        self.assertEqual(naa.get_volume_id(), 0x18c)
        self.assertEqual(naa.get_system_serial(), 0x4e2b)
        self.assertEqual(naa.get_ieee_company_id(), NFINIDAT_IEEE)
        self.assertEqual(str(naa), "naa." + TEST_NAA)
