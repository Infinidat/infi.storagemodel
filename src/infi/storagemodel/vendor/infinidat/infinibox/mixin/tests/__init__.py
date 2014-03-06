from json import dumps
from infi import unittest
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
        return dumps(pages[page])

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

        return dumps(pages[page])

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
        from ...string_page import StringInquiryPageData
        device = PeripheralDeviceDataBuffer(qualifier=0, type=0)
        volume_name = StringInquiryPageData(peripheral_device=device, page_code=0xc7, string="volume_name")
        host_name = StringInquiryPageData(peripheral_device=device, page_code=0xc8, string="host_name")
        cluster_name = StringInquiryPageData(peripheral_device=device, page_code=0xc9, string="cluster_name")
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
