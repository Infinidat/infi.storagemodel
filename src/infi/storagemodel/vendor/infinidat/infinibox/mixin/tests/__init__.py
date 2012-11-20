from json import dumps
from infi import unittest
from .. import scsi_block_class, scsi_controller_class

class UnauthenticatedController(scsi_controller_class):
    def get_device_identification_page(self):
        return self

    def get_vendor_specific_dict(self):
        return {'host': '0000000000000000',
                'cluster': '0000000000000000'}

    def _get_json_inquiry_data(self):
        return dumps({u'host': None,
                u'host_entity_id': 0,
                u'cluster': None,
                u'cluster_entity_id': 0,
                u'system_name': u'box-ci09',
                u'system_serial': 20011,
                u'system_version': u'0.4.1',
                u'vol': None,
                u'vol_entity_id': 0})

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

    def _get_json_inquiry_data(self):
        return dumps({u'host': u'name',
                u'host_entity_id': 1,
                u'cluster': u'name',
                u'cluster_entity_id': 2,
                u'system_name': u'box-ci09',
                u'system_serial': 20011,
                u'system_version': u'0.4.1',
                u'vol': u'name',
                u'vol_entity_id': 1})

    def get_naa(self):
        return self

    def get_volume_id(self):
        return 1

class JSONInquiryTestCase(unittest.TestCase):
    def test_inquiry_to_unauthenticated_controller(self):
        device = UnauthenticatedController(None)
        self.assertEqual(device.get_host_id(), 0)
        self.assertEqual(device.get_host_name(), None)
        self.assertEqual(device.get_system_serial(), 20011)
        self.assertEqual(device.get_system_name(), 'box-ci09')
        self.assertEqual(device.get_cluster_id(), 0)
        self.assertEqual(device.get_cluster_name(), None)

    def test_inquiry_to_volume(self):
        device = MappedVolumed(None)
        self.assertEqual(device.get_host_id(), 1)
        self.assertEqual(device.get_host_name(), 'name')
        self.assertEqual(device.get_cluster_id(), 2)
        self.assertEqual(device.get_cluster_name(), 'name')
        self.assertEqual(device.get_volume_id(), 1)
        self.assertEqual(device.get_volume_name(), 'name')
