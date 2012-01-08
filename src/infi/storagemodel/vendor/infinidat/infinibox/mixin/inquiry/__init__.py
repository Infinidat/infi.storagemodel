
from infi.pyutils.lazy import cached_method

from logging import getLogger
log = getLogger()

class DeviceIdentificationPage(object):
    def __init__(self, page):
        self._page = page

    def is_designator_vendor_specific(self, designator):
        from infi.asi.cdb.inquiry.vpd_pages.device_identification.designators import VendorSpecificDesignator
        return isinstance(designator, VendorSpecificDesignator)

    def filter_vendor_specific_designators(self):
        return filter(self.is_designator_vendor_specific, self._page.designators_list)

    @cached_method
    def get_vendor_specific_dict(self):
        result = dict()
        for designator in self.filter_vendor_specific_designators():
            key, value = [item.strip() for item in designator.vendor_specific_identifier.split('=', 1)]
            result[key] = value
        return result

    @cached_method
    def get_naa(self):
        from infi.asi.cdb.inquiry.vpd_pages.device_identification import designators
        naa = designators.NAA_IEEE_Registered_Extended_Designator
        from ...naa import InfinidatNAA
        for designator in self._page.designators_list:
            if isinstance(designator, naa):
                return InfinidatNAA(designator)

    @cached_method
    def get_target_port_group(self):
        """:returns: the target port group
        :rtype: int"""
        from infi.asi.cdb.inquiry.vpd_pages.device_identification.designators import TargetPortGroupDesignator
        for designator in self._page.designators_list:
            if isinstance(designator, TargetPortGroupDesignator):
                return designator.target_port_group

    @cached_method
    def get_relative_target_port_group(self):
        """:returns: the relative target port group
        :rtype: int"""
        from infi.asi.cdb.inquiry.vpd_pages.device_identification.designators import RelativeTargetPortDesignator
        for designator in self._page.designators_list:
            if isinstance(designator, RelativeTargetPortDesignator):
                return designator.relative_target_port_identifier

class InfiniBoxInquiryMixin(object):
    @cached_method
    def get_device_identification_page(self):
        raw = self.device.get_scsi_inquiry_pages()[0x83]
        return DeviceIdentificationPage(raw)

    @cached_method
    def get_management_address(self):
        """:returns: the management IPv4 address of the InfiniBox
        :rtype: string"""
        return self.get_device_identification_page().get_vendor_specific_dict()['ip']

    @cached_method
    def get_management_port(self):
        """:returns: the management IPv4 port of the InfiniBox
        :rtype: string"""
        return int(self.get_device_identification_page().get_vendor_specific_dict()['port'])

    @cached_method
    def get_host_id(self):
        """:returns: the host id within the InfiniBox
        :rtype: int"""
        return int(self.get_device_identification_page().get_vendor_specific_dict()['host'], 16)

    @cached_method
    def get_naa(self):
        """:returns: the infinidat naa
        :rtype: :class:`.InfinidatNAA`"""
        return self.get_device_identification_page().get_naa()

    @cached_method
    def get_target_port_group(self):
        """:returns: the target port group
        :rtype: int"""
        return self.get_device_identification_page().get_target_port_group()

    @cached_method
    def get_relative_target_port_group(self):
        """:returns: the relative target port group
        :rtype: int"""
        return self.get_device_identification_page().get_relative_target_port_group()

    @cached_method
    def get_fc_port(self):
        """:rtype: :class:`.InfinidatFiberChannelPort`"""
        from ...fc_port import InfinidatFiberChannelPort
        return InfinidatFiberChannelPort(self.get_relative_target_port_group(),
                                         self.get_target_port_group())

    def _get_json_inquiry_page(self):
        from infi.asi.coroutines.sync_adapter import sync_wait
        from ...json_page import JSONInquiryPageCommand
        with self.device.asi_context() as asi:
            inquiry_command = JSONInquiryPageCommand()
            return sync_wait(inquiry_command.execute(asi))

    @cached_method
    def get_json_data(self):
        """:returns: the json inquiry data from the system
        :rtype: dict"""
        from json import loads
        inquiry_page = self._get_json_inquiry_page()
        raw_data = inquiry_page.json_serialized_data
        return loads(raw_data)
