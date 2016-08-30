from infi.storagemodel.errors import check_for_insufficient_resources
from infi.exceptools import InfiException, chain
from infi.pyutils.lazy import cached_method
from contextlib import contextmanager
import binascii
import infi.instruct
from logging import getLogger
logger = getLogger(__name__)

class InquiryException(InfiException):
    pass

class DeviceIdentificationPage(object):
    def __init__(self, page):
        self._page = page

    def is_designator_vendor_specific(self, designator):
        from infi.asi.cdb.inquiry.vpd_pages.designators import VendorSpecificDesignator
        return isinstance(designator, VendorSpecificDesignator)

    def filter_vendor_specific_designators(self):
        return list(filter(self.is_designator_vendor_specific, self._page.designators_list))

    @cached_method
    def get_vendor_specific_dict(self):
        result = dict()
        for designator in self.filter_vendor_specific_designators():
            key, value = [item.strip() for item in designator.vendor_specific_identifier.split('=', 1)]
            result[key] = value
        return result

    @cached_method
    def get_naa(self):
        """ Returns the Infinidat NAA (`infi.storagemodel.vendor.infinidat.infinibox.naa.InfinidatNAA`) """
        from infi.asi.cdb.inquiry.vpd_pages import designators
        naa = designators.NAA_IEEE_Registered_Extended_Designator
        from ...naa import InfinidatNAA
        for designator in self._page.designators_list:
            if isinstance(designator, naa):
                return InfinidatNAA(designator)

    @cached_method
    def get_target_port_group(self):
        """ Returns the target port group number. """
        from infi.asi.cdb.inquiry.vpd_pages.designators import TargetPortGroupDesignator
        for designator in self._page.designators_list:
            if isinstance(designator, TargetPortGroupDesignator):
                return designator.target_port_group

    @cached_method
    def get_relative_target_port_group(self):
        """ Returns the relative target port group number. """
        from infi.asi.cdb.inquiry.vpd_pages.designators import RelativeTargetPortDesignator
        for designator in self._page.designators_list:
            if isinstance(designator, RelativeTargetPortDesignator):
                return designator.relative_target_port_identifier


def translate_hex_repr_string(hex_repr):
    binary_string = binascii.unhexlify(hex_repr)
    return getattr(infi.instruct, "SBInt64").create_from_string(binary_string)

def _is_exception_of_unsupported_inquiry_page(error):
    return error.sense_obj.sense_key == 'ILLEGAL_REQUEST' and \
        error.sense_obj.additional_sense_code.code_name == 'INVALID FIELD IN CDB'

class InfiniBoxInquiryMixin(object):

    @cached_method
    def get_device_identification_page(self):
        raw = self.device.get_scsi_inquiry_pages()[0x83]
        return DeviceIdentificationPage(raw)

    @cached_method
    def get_naa(self):
        """ Returns the Infinidat NAA (`infi.storagemodel.vendor.infinidat.infinibox.naa.InfinidatNAA`) """
        return self.get_device_identification_page().get_naa()

    @cached_method
    def get_target_port_group(self):
        """ Returns the target port group number. """
        return self.get_device_identification_page().get_target_port_group()

    @cached_method
    def get_relative_target_port_group(self):
        """ Returns the relative target port group number. """
        return self.get_device_identification_page().get_relative_target_port_group()

    @cached_method
    def get_fc_port(self):
        """ Returns an `infi.storagemodel.vendor.infinidat.infinibox.fc_port.InfinidatFiberChannelPort`"""
        from ...fc_port import InfinidatFiberChannelPort
        return InfinidatFiberChannelPort(self.get_relative_target_port_group(),
                                         self.get_target_port_group())

    @check_for_insufficient_resources
    def _get_json_inquiry_page(self, page=0xc5):
        from infi.asi import AsiCheckConditionError
        from infi.storagemodel.vendor.infinidat.infinibox.json_page import JSONInquiryPageBuffer
        try:
            unknown_page = self.device.get_scsi_inquiry_pages()[page]
            json_page = JSONInquiryPageBuffer()
            json_page.unpack(unknown_page.pack())
            return json_page
        except AsiCheckConditionError as error:
            if _is_exception_of_unsupported_inquiry_page(error):
                raise chain(InquiryException("JSON Inquiry command error"))
            raise

    @check_for_insufficient_resources
    def _get_string_inquiry_page(self, page):
        from infi.asi import AsiCheckConditionError
        from infi.storagemodel.vendor.infinidat.infinibox.string_page import StringInquiryPageBuffer
        try:
            unknown_page = self.device.get_scsi_inquiry_pages()[page]
            string_page = StringInquiryPageBuffer()
            string_page.unpack(unknown_page.pack())
            return string_page
        except KeyError:
            raise chain(InquiryException("Inquiry command error"))
        except AsiCheckConditionError as error:
            if _is_exception_of_unsupported_inquiry_page(error):
                raise chain(InquiryException("Inquiry command error"))
            raise

    def _get_json_inquiry_data(self, page):
        return self._get_json_inquiry_page(page).json_data

    def _get_string_inquiry_data(self, page):
        return self._get_string_inquiry_page(page).string.strip()

    @cached_method
    def get_json_data(self, page=0xc5):
        """ Returns the json inquiry data from the system as a `dict` """
        try:
            return self._get_json_inquiry_data(page)
        except ValueError:
            logger.exception("Inquiry response is invalid JSON format")
            raise chain(InquiryException("ValueError"))

    @cached_method
    def get_string_data(self, page):
        """ Returns the string inquiry data from the system as a `dict` """
        from json import loads
        return self._get_string_inquiry_data(page)
