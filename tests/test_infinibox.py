from infi.unittest import TestCase
from infi.asi.cdb.inquiry.vpd_pages.device_identification import DeviceIdentificationVPDPageData
from infi.asi.cdb.inquiry.vpd_pages.device_identification import designators
from infi.asi.cdb.inquiry.vpd_pages.device_identification import PeripheralDeviceData

DIRECT_ACCESS_BLOCK_DEVICE = 0
STORAGE_ARRAY_CONTROLLER_DEVICE = 12

from infi.instruct import Struct, UBInt8, UBInt16
from logging import getLogger

log = getLogger()

class PageCode(Struct):
    _fields_ = [UBInt8("page_code"),
                UBInt16("page_length"), ]

DEFAULT_ATTRIBUTES = dict(protocol_identifier=0,
                          piv=0,
                          association=0,
                          reserved=0,)

class InquiryPageMock(object):
    def __init__(self):
        super(InquiryPageMock, self).__init__()

    def _append_to_page(self, page, struct):
        addition = struct.write_to_string(struct)
        log.debug("adding %r to page (length=%s)", addition, len(addition))
        page += addition
        log.debug("updated page size = %s", len(page))
        return page

    def get_device_identification_page(self, device_type, host_id, volume_id):
        raw_data = self.get_device_identification_page__raw(device_type, host_id, volume_id)
        log.debug("length of raw data = %s", len(raw_data))
        log.debug("raw data = {!r}".format(raw_data))
        return DeviceIdentificationVPDPageData.create_from_string(raw_data)

    def get_device_identification_page__raw(self, device_type, host_id, volume_id):
        raw_data = ''
        device = self._get_peripheral_device(device_type)
        designators = self._get_device_identification_page__designators(device_type, host_id, volume_id)
        page_info = PageCode(page_code=0x83, page_length=len(designators))
        for item in [device, page_info]:
            raw_data = self._append_to_page(raw_data, item)
        raw_data += designators
        return raw_data

    def _get_device_identification_page__designators(self, device_type, host_id, volume_id):
        designators = ''
        designators = self._append_to_page(designators, self._get_naa())
        designators = self._append_to_page(designators, self._get_management_network_address())
        designators = self._append_to_page(designators, self._get_management_network_port())
        designators = self._append_to_page(designators, self._get_relative_target_port_identifier())
        designators = self._append_to_page(designators, self._get_target_port_group())
        designators = self._append_to_page(designators, self._get_host_id(host_id))
        return designators

    def _set_attributes_in_designator(self, designator, attributes):
        for key, value in attributes.iteritems():
            log.debug("setting %s to %s", key, value)
            setattr(designator, key, value)
        return designator

    def _get_peripheral_device(self, device_type):
        device = PeripheralDeviceData()
        device.qualifier = 0x0b
        device.type = device_type
        return device

    def _get_naa(self):
        designator = designators.NAA_IEEE_Registered_Extended_Designator()
        attributes = dict(code_set=1,
                          designator_type=3,
                          designator_length=8,
                          naa=6,
                          ieee_company_id__high=1, # TODO put real value
                          ieee_company_id__low=1, # TODO put real value
                          ieee_company_id__middle=1, # TODO put real value
                          vendor_specific_identifier_extension=1, # TODO put real value
                          vendor_specific_identifier__low=0,
                          vendor_specific_identifier__high=0
                          )
        attributes.update(DEFAULT_ATTRIBUTES)
        self._set_attributes_in_designator(designator, attributes)
        return designator

    def _get_management_network_port(self):
        designator = designators.VendorSpecificDesignator()
        attributes = dict(code_set=2,
                          designator_type=0,
                          designator_length=9,
                          vendor_specific_identifier="port=8080"
                          )
        attributes.update(DEFAULT_ATTRIBUTES)
        self._set_attributes_in_designator(designator, attributes)
        return designator


    def _get_management_network_address(self):
        designator = designators.VendorSpecificDesignator()
        attributes = dict(code_set=2,
                          designator_type=0,
                          designator_length=18,
                          vendor_specific_identifier="ip=255.255.255.255"
                          )
        attributes.update(DEFAULT_ATTRIBUTES)
        self._set_attributes_in_designator(designator, attributes)
        return designator

    def _get_relative_target_port_identifier(self):
        designator = designators.RelativeTargetPortDesignator()
        attributes = dict(code_set=1,
                          designator_type=4,
                          designator_length=4,
                          relative_target_port_identifier=0
                          )
        attributes.update(DEFAULT_ATTRIBUTES)
        self._set_attributes_in_designator(designator, attributes)
        return designator

    def _get_target_port_group(self):
        designator = designators.TargetPortGroupDesignator()
        attributes = dict(code_set=1,
                          designator_type=5,
                          designator_length=4,
                          target_port_group=0
                          )
        attributes.update(DEFAULT_ATTRIBUTES)
        self._set_attributes_in_designator(designator, attributes)
        return designator

    def _get_host_id(self, id):
        designator = designators.VendorSpecificDesignator()
        attributes = dict(code_set=2,
                          designator_type=0,
                          designator_length=64,
                          vendor_specific_identifier="host={}".format(str(id).zfill(59)))
        attributes.update(DEFAULT_ATTRIBUTES)
        self._set_attributes_in_designator(designator, attributes)
        return designator

class InquiryPageTestCase(TestCase):
    def setUp(self):
        self.mock = InquiryPageMock()

    def test_page_mock(self):
        page = self.mock.get_device_identification_page(DIRECT_ACCESS_BLOCK_DEVICE, 1, 2)

    def test_host_id(self):
        designator = self.mock._get_host_id(1)
        self.assertEqual(designator.sizeof(designator), 68)

    def test_naa(self):
        designator = self.mock._get_naa()
        self.assertEqual(designator.sizeof(designator), 20)

    def test_rtpg(self):
        rtpi = self.mock._get_relative_target_port_identifier()
        tpg = self.mock._get_target_port_group()
        self.assertEqual(rtpi.sizeof(rtpi), 8)
        self.assertEqual(tpg.sizeof(tpg), 8)

    def test_management_address(self):
        designator = self.mock._get_management_network_address  ()
        self.assertEqual(designator.sizeof(designator), 22)

    def test_designators(self):
        designators = self.mock._get_device_identification_page__designators(DIRECT_ACCESS_BLOCK_DEVICE, 1, 1)
        self.assertEqual(len(designators), 139)

    def test_empty_page(self):
        raw_data = ''
        device = self.mock._get_peripheral_device(DIRECT_ACCESS_BLOCK_DEVICE)
        designators = ''
        page_info = PageCode(page_code=0x83, page_length=len(designators))
        for item in [device, page_info]:
            raw_data = self.mock._append_to_page(raw_data, item)
        raw_data += designators
        return DeviceIdentificationVPDPageData.create_from_string(raw_data)

from mock import patch, Mock
from infi.storagemodel.vendor.infinibox import InfiniBoxMixin, InfiniBoxVolumeMixin

class MixinWithDevice(InfiniBoxVolumeMixin, InfiniBoxMixin):
    def get_scsi_inquiry_pages(self):
        pages = {}
        pages[0x83] = InquiryPageMock().get_device_identification_page(1, 1 , 1)
        return pages

    def _is_volume_mapped(self):
        return True

    def __init__(self):
        super(MixinWithDevice, self).__init__()
        self.device = self
        self.device.get_scsi_inquiry_pages = self.get_scsi_inquiry_pages

class MixinTestCase(TestCase):
    def setUp(self):
        self.mixin = MixinWithDevice()

    def test_management_address(self):
        self.assertEqual(self.mixin.get_box_management_address(), "255.255.255.255")
        self.assertEqual(self.mixin.get_box_management_port(), 8080)

    def test_host_id(self):
        self.assertEqual(self.mixin.get_host_id(), 1)

    def test_volume_id(self):
        self.assertEqual(self.mixin.get_volume_id(), 1)
