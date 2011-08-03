import unittest
from infi.storagemodel.dtypes import hctl

subject = hctl.HCTL(1, 0, 0, 1)

class HCTLTestCase(unittest.TestCase):
    def test_getters(self):
        self.assertEqual(subject.get_host(), 1)
        self.assertEqual(subject.get_channel(), 0)
        self.assertEqual(subject.get_target(), 0)
        self.assertEqual(subject.get_lun(), 1)

    def test_fromstring(self):
        self.assertEqual(subject, hctl.HCTL.from_string("1:0:0:1"))
        self.assertNotEqual(subject, hctl.HCTL.from_string("1:0:0:2"))
        self.assertLessEqual(subject, hctl.HCTL.from_string("1:0:0:2"))

    def test_opeators(self):
        self.assertEqual(subject, "1:0:0:1")
        self.assertFalse(subject == 123)
        self.assertRaises(TypeError, subject.__lt__, None)
        self.assertGreaterEqual(subject, hctl.HCTL.from_string("1:0:0:0"))
        self.assertGreater(subject, hctl.HCTL.from_string("1:0:0:0"))
        self.assertEqual([i for i in subject], [1, 0, 0, 1])
        self.assertRaises(ValueError, subject.from_string, None)
        self.assertEqual(repr(subject), "<1:0:0:1>")
        self.assertEqual(hctl.HCT(1, 0, 0)[1], subject)
