from infi.pyutils.lazy import cached_method, LazyImmutableDict
from infi.storagemodel.errors import check_for_scsi_errors
#pylint: disable=E1002,W0622

class SupportedVPDPagesDict(LazyImmutableDict):
    def __init__(self, dict, device):
        super(SupportedVPDPagesDict, self).__init__(dict.copy())
        self.device = device

    @check_for_scsi_errors
    def _create_value(self, page_code):
        from infi.asi.cdb.inquiry.vpd_pages import get_vpd_page
        from infi.asi.coroutines.sync_adapter import sync_wait
        with self.device.asi_context() as asi:
            inquiry_command = get_vpd_page(page_code)()
            return sync_wait(inquiry_command.execute(asi))

    def __repr__(self):
        return "<Supported VPD Pages for {!r}: {!r}>".format(self.device, self.keys())

class InquiryInformationMixin(object):
    @cached_method
    def get_scsi_vendor_id(self):
        """:returns: the T10 vendor identifier string, as give in SCSI Standard Inquiry
        :rtype: string"""
        return self.get_scsi_standard_inquiry().t10_vendor_identification.strip()

    @cached_method
    def get_scsi_product_id(self):
        """:returns: the T10 product identifier string, as give in SCSI Standard Inquiry
        :rtype: string"""
        return self.get_scsi_standard_inquiry().product_identification.strip()

    @cached_method
    def get_scsi_vid_pid(self):
        """:returns: a tuple of the vendor_id and product_id
        :rtype: tuple"""
        return (self.get_scsi_vendor_id(), self.get_scsi_product_id())

    @cached_method
    @check_for_scsi_errors
    def get_scsi_inquiry_pages(self):
        """Returns an immutable dict-like object of available inquiry pages from this device.
        For example:

            >>> dev.scsi_inquiry_pages[0x80].product_serial_number
        """
        from infi.asi.cdb.inquiry.vpd_pages import INQUIRY_PAGE_SUPPORTED_VPD_PAGES
        from infi.asi.cdb.inquiry.vpd_pages import SupportedVPDPagesCommand
        from infi.asi import AsiCheckConditionError
        from infi.asi.coroutines.sync_adapter import sync_wait
        command = SupportedVPDPagesCommand()

        page_dict = {}
        try:
            with self.asi_context() as asi:
                data = sync_wait(command.execute(asi))
                page_dict[INQUIRY_PAGE_SUPPORTED_VPD_PAGES] = data
                for page_code in data.vpd_parameters:
                    page_dict[page_code] = None
        except AsiCheckConditionError, e:
            (key, code) = (e.sense_obj.sense_key, e.sense_obj.additional_sense_code.code_name)
            if (key, code) == ('ILLEGAL_REQUEST', 'INVALID FIELD IN CDB'):
                # There are devices such as virtual USB disk controllers (bladecenter stuff) that don't support this
                # (mandatory!) command. In this case we simply return an empty dict.
                pass
            else:
                raise
        return SupportedVPDPagesDict(page_dict, self)

    @cached_method
    def get_scsi_serial_number(self):
        """:returns: the SCSI serial of the device or an empty string ("") if not available
        :rtype: string"""
        from infi.asi.cdb.inquiry.vpd_pages import INQUIRY_PAGE_UNIT_SERIAL_NUMBER
        serial = ''
        if INQUIRY_PAGE_UNIT_SERIAL_NUMBER in self.get_scsi_inquiry_pages():
            serial = self.get_scsi_inquiry_pages()[INQUIRY_PAGE_UNIT_SERIAL_NUMBER].product_serial_number
        return serial

    @cached_method
    @check_for_scsi_errors
    def get_scsi_standard_inquiry(self):
        """:returns: the standard inquiry data"""
        from infi.asi.cdb.inquiry.standard import StandardInquiryCommand
        from infi.asi.coroutines.sync_adapter import sync_wait
        with self.asi_context() as asi:
            command = StandardInquiryCommand()
            return sync_wait(command.execute(asi))

    @check_for_scsi_errors
    def get_scsi_test_unit_ready(self):
        """:returns: True if the device is ready
        """
        from infi.asi.cdb.tur import TestUnitReadyCommand
        from infi.asi.coroutines.sync_adapter import sync_wait
        with self.asi_context() as asi:
            command = TestUnitReadyCommand()
            return sync_wait(command.execute(asi))

