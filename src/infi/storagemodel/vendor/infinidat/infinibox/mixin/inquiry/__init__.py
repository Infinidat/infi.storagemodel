
from infi.pyutils.lazy import cached_method

from logging import getLogger
log = getLogger()

class InfiniBoxInquiryMixin(object):
    @cached_method
    def get_management_address(self):
        """:returns: the management IPv4 address of the InfiniBox
        :rtype: string"""
        from infi.asi.cdb.inquiry.vpd_pages.device_identification.designators import VendorSpecificDesignator
        device_identification_page = self.device.get_scsi_inquiry_pages()[0x83]
        designators = device_identification_page.designators_list
        for designator in designators:
            log.debug("checking designator type %s %d of %d", designator.__class__.__name__,
                      designators.index(designator), len(designators))

            if isinstance(designator, VendorSpecificDesignator):
                value = designator.vendor_specific_identifier
                if value.startswith("ip"):
                    log.debug("SCSINameDesginator string = %r", value)
                    return value.split("=")[1].strip()

    @cached_method
    def get_management_port(self):
        """:returns: the management IPv4 port of the InfiniBox
        :rtype: string"""
        from infi.asi.cdb.inquiry.vpd_pages.device_identification.designators import VendorSpecificDesignator
        device_identification_page = self.device.get_scsi_inquiry_pages()[0x83]
        designators = device_identification_page.designators_list
        for designator in designators:
            log.debug("checking designator type %s %d of %d", designator.__class__.__name__,
                      designators.index(designator), len(designators))

            if isinstance(designator, VendorSpecificDesignator):
                value = designator.vendor_specific_identifier
                if value.startswith("port"):
                    log.debug("SCSINameDesginator string = %r", value)
                    return int(value.split("=")[1].strip())

    @cached_method
    def get_host_id(self):
        """:returns: the host id within the InfiniBox
        :rtype: int"""
        from infi.asi.cdb.inquiry.vpd_pages.device_identification.designators import VendorSpecificDesignator
        device_identification_page = self.device.get_scsi_inquiry_pages()[0x83]
        for designator in device_identification_page.designators_list:
            if isinstance(designator, VendorSpecificDesignator):
                value = designator.vendor_specific_identifier
                if value.startswith("host"):
                    return int(value.split("=")[1].strip())

    @cached_method
    def get_naa(self):
        """:returns: the infinidat naa
        :rtype: :class:`.InfinidatNAA`"""
        from infi.asi.cdb.inquiry.vpd_pages.device_identification import designators
        from ...naa import InfinidatNAA
        naa = designators.NAA_IEEE_Registered_Extended_Designator
        device_identification_page = self.device.get_scsi_inquiry_pages()[0x83]
        for designator in device_identification_page.designators_list:
            if isinstance(designator, naa):
                return InfinidatNAA(designator)

    @cached_method
    def get_target_port_group(self):
        """:returns: the target port group
        :rtype: int"""
        from infi.asi.cdb.inquiry.vpd_pages.device_identification.designators import TargetPortGroupDesignator
        device_identification_page = self.device.get_scsi_inquiry_pages()[0x83]
        for designator in device_identification_page.designators_list:
            if isinstance(designator, TargetPortGroupDesignator):
                return designator.target_port_group

    @cached_method
    def get_relative_target_port_group(self):
        """:returns: the relative target port group
        :rtype: int"""
        from infi.asi.cdb.inquiry.vpd_pages.device_identification.designators import RelativeTargetPortDesignator
        device_identification_page = self.device.get_scsi_inquiry_pages()[0x83]
        for designator in device_identification_page.designators_list:
            if isinstance(designator, RelativeTargetPortDesignator):
                return designator.relative_target_port_identifier

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
