from json import dumps
from infi import unittest
from infi.storagemodel.errors import check_for_insufficient_resources
from .. import scsi_block_class, scsi_controller_class


class UnauthenticatedController(scsi_controller_class):
    def get_device_identification_page(self):
        return self

    def get_vendor_specific_dict(self):
        return {'host': '0000000000000000',
                'cluster': '0000000000000000'}

    def _get_json_inquiry_data(self, page):
        pages = {
                    0xc5: {
                        u'host': None,
                        u'host_entity_id': 0,
                        u'cluster': None,
                        u'cluster_entity_id': 0,
                        u'system_name': u'box-ci09',
                        u'system_serial': 20011,
                        u'system_version': u'0.4.1',
                        u'vol': None,
                        u'vol_entity_id': 0,
                    },
                    0xc6: {
                        u'host_entity_id': 0,
                        u'cluster_entity_id': 0,
                        u'system_name': u'box-ci09',
                        u'system_serial': 20011,
                        u'system_version': u'0.4.1',
                        u'vol_entity_id': 0,
                    },
                }
        return pages[page]

    def get_naa(self):
        return self

    def get_system_serial(self):
        return 20011


class MappedVolumed(scsi_block_class):
    def get_device_identification_page(self):
        return self

    def get_vendor_specific_dict(self):
        return {'host': '0000000000000001',
                'cluster': '0000000000000002',
                }

    def _get_json_inquiry_data(self, page):
        pages = {
                    0xc5: {
                        u'host': u'name',
                        u'host_entity_id': 1,
                        u'cluster': u'name',
                        u'cluster_entity_id': 2,
                        u'system_name': u'box-ci09',
                        u'system_serial': 20011,
                        u'system_version': u'0.4.1',
                        u'vol': u'name',
                        u'vol_entity_id': 1,
                    },
                    0xc6: {
                        u'host_entity_id': 1,
                        u'cluster_entity_id': 2,
                        u'system_name': u'box-ci09',
                        u'system_serial': 20011,
                        u'system_version': u'0.4.1',
                        u'vol_entity_id': 1,
                    },
                }

        return pages[page]

    def get_naa(self):
        return self

    def get_volume_id(self):
        return 1


class LegacyDevice(object):
    def get_scsi_inquiry_pages(self):
        return {}

class NewDevice(object):
    def get_scsi_inquiry_pages(self):
        from infi.asi.cdb.inquiry import PeripheralDeviceDataBuffer
        from infi.storagemodel.vendor.infinidat.infinibox.string_page import StringInquiryPageBuffer
        device = PeripheralDeviceDataBuffer(qualifier=0, type=0)
        volume_name = StringInquiryPageBuffer(peripheral_device=device, page_code=0xc7, string="volume_name")
        host_name = StringInquiryPageBuffer(peripheral_device=device, page_code=0xc8, string="host_name")
        cluster_name = StringInquiryPageBuffer(peripheral_device=device, page_code=0xc9, string="cluster_name")
        return {
            0xc7: volume_name,
            0xc8: host_name,
            0xc9: cluster_name,
        }

class InfiniBoxInquiryTestCase(unittest.TestCase):
    def test_inquiry_to_unauthenticated_controller__without_pages_added_to_15(self):
        device = UnauthenticatedController(LegacyDevice())
        self.assertEqual(device.get_host_id(), 0)
        self.assertEqual(device.get_host_name(), None)
        self.assertEqual(device.get_system_serial(), 20011)
        self.assertEqual(device.get_system_name(), 'box-ci09')
        self.assertEqual(device.get_cluster_id(), 0)
        self.assertEqual(device.get_cluster_name(), None)

    def test_inquiry_to_volume__without_pages_added_to_15(self):
        device = MappedVolumed(LegacyDevice())
        self.assertEqual(device.get_host_id(), 1)
        self.assertEqual(device.get_host_name(), 'name')
        self.assertEqual(device.get_cluster_id(), 2)
        self.assertEqual(device.get_cluster_name(), 'name')
        self.assertEqual(device.get_volume_id(), 1)
        self.assertEqual(device.get_volume_name(), 'name')

    def test_inquiry_to_volume__without_pages_added_to_15(self):
        device = MappedVolumed(NewDevice())
        self.assertEqual(device.get_host_id(), 1)
        self.assertEqual(device.get_host_name(), 'host_name')
        self.assertEqual(device.get_cluster_id(), 2)
        self.assertEqual(device.get_cluster_name(), 'cluster_name')
        self.assertEqual(device.get_volume_id(), 1)
        self.assertEqual(device.get_volume_name(), 'volume_name')

class InsufficientResourcesTestCase(unittest.TestCase):
    def setUp(self):
        from infi.asi.sense import SCSISenseDataDescriptorBased
        from infi.asi.errors import AsiCheckConditionError
        from binascii import unhexlify

        buf = b"720555030000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
        sense_obj = SCSISenseDataDescriptorBased.create_from_string(unhexlify(buf))
        self._check_condition_exception = AsiCheckConditionError(buf, sense_obj)

        other_buf = b"720555040000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
        other_sense_obj = SCSISenseDataDescriptorBased.create_from_string(unhexlify(other_buf))
        self._other_exception = AsiCheckConditionError(other_buf, other_sense_obj)


    def test_once(self):
        self._count = 0
        @check_for_insufficient_resources
        def func():
            if self._count == 0:
                self._count += 1
                raise self._check_condition_exception
            return 'asd'
        self.assertEqual(func(), 'asd')

    def test_infinite(self):
        from infi.storagemodel.errors import InsufficientResourcesError
        @check_for_insufficient_resources
        def func():
            raise self._check_condition_exception
        with self.assertRaises(InsufficientResourcesError):
            func()

    def test_other_error(self):
        from infi.asi.errors import AsiCheckConditionError
        @check_for_insufficient_resources
        def func():
            raise self._other_exception
        with self.assertRaises(AsiCheckConditionError):
            func()

    def test_other_exception(self):
        @check_for_insufficient_resources
        def func():
            raise IndexError
        with self.assertRaises(IndexError):
            func()
