from infi.pyutils.lazy import cached_method, LazyImmutableDict
from infi.storagemodel.errors import check_for_scsi_errors, StorageModelError
from logging import getLogger
logger = getLogger(__name__)
#pylint: disable=E1002,W0622

__all__ = ['InquiryInformationMixin']


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
        return "<Supported VPD Pages for {!r}: {!r}>".format(self.device, sorted(self.keys()))


class InquiryInformationMixin(object):
    @cached_method
    def get_scsi_vendor_id_or_unknown_on_error(self):
        """Returns ('<unknown>', '<unknown>') on unexpected error instead of raising exception"""
        try:
            return self.get_scsi_vid_pid()
        except:
            logger.exception("failed to get scsi vid/pid")
            return ('<unknown>', '<unknown>')

    @cached_method
    def get_scsi_vendor_id(self):
        """Returns the stripped T10 vendor identifier string, as give in SCSI Standard Inquiry"""
        return self.get_scsi_standard_inquiry().t10_vendor_identification.strip()

    @cached_method
    def get_scsi_revision(self):
        """Returns the stripped T10 revision string, as give in SCSI Standard Inquiry"""
        return self.get_scsi_standard_inquiry().product_revision_level.strip()

    @cached_method
    def get_scsi_product_id(self):
        """Returns the stripped T10 product identifier string, as give in SCSI Standard Inquiry"""
        return self.get_scsi_standard_inquiry().product_identification.strip()

    @cached_method
    def get_scsi_vid_pid(self):
        """Returns a tuple of the vendor_id and product_id"""
        return (self.get_scsi_vendor_id(), self.get_scsi_product_id())

    @cached_method
    def get_scsi_vid_pid_rev(self):
        """Returns a tuple of the vendor_id, product_id and revision"""
        return (self.get_scsi_vendor_id(), self.get_scsi_product_id(), self.get_scsi_revision())

    @cached_method
    @check_for_scsi_errors
    def get_scsi_inquiry_pages(self):
        """Returns an immutable dict-like object of available inquiry pages from this device.
        For example:

            >>> device.get_scsi_inquiry_pages()[0x80].product_serial_number
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
        except AsiCheckConditionError as e:
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
        """Returns the SCSI serial string of the device or an empty string ("") if not available"""
        from infi.asi.cdb.inquiry.vpd_pages import INQUIRY_PAGE_UNIT_SERIAL_NUMBER
        serial = ''
        if INQUIRY_PAGE_UNIT_SERIAL_NUMBER in self.get_scsi_inquiry_pages():
            serial = self.get_scsi_inquiry_pages()[INQUIRY_PAGE_UNIT_SERIAL_NUMBER].product_serial_number
        # keep the serial in the class for _get_scsi_serial_for_repr
        self._serial = serial
        return serial

    @cached_method
    def get_scsi_ata_information(self):
        """Returns the SCSI ata information of the device as a dict of dicts for SATL and identify device"""
        from infi.asi.cdb.inquiry.vpd_pages import INQUIRY_PAGE_ATA_INFORMATION
        ata_info = dict(sat=dict(), device=dict())
        if INQUIRY_PAGE_ATA_INFORMATION in self.get_scsi_inquiry_pages():
            ata_info['sat']['vendor'] = self.get_scsi_inquiry_pages()[INQUIRY_PAGE_ATA_INFORMATION].sat_vendor_identification
            ata_info['sat']['model'] = self.get_scsi_inquiry_pages()[INQUIRY_PAGE_ATA_INFORMATION].sat_product_identification
            ata_info['sat']['rev'] = self.get_scsi_inquiry_pages()[INQUIRY_PAGE_ATA_INFORMATION].sat_product_revision_level
            ata_info['device']['serial_number'] = \
                self.get_scsi_inquiry_pages()[INQUIRY_PAGE_ATA_INFORMATION].identify_device.serial_number
            ata_info['device']['model'] = \
                self.get_scsi_inquiry_pages()[INQUIRY_PAGE_ATA_INFORMATION].identify_device.model_number
            ata_info['device']['rev'] = \
                self.get_scsi_inquiry_pages()[INQUIRY_PAGE_ATA_INFORMATION].identify_device.firmware_revision
        return ata_info

    @cached_method
    @check_for_scsi_errors
    def get_scsi_standard_inquiry(self):
        """Returns the standard inquiry data"""
        from infi.asi import AsiCheckConditionError
        from infi.asi.coroutines.sync_adapter import sync_wait
        from infi.asi.cdb.inquiry.standard import StandardInquiryCommand, STANDARD_INQUIRY_MINIMAL_DATA_LENGTH

        def _get_scsi_standard_inquiry_the_fastest_way(allocation_length=219):
            try:
                with self.asi_context() as asi:
                    command = StandardInquiryCommand(allocation_length=allocation_length)
                    return sync_wait(command.execute(asi))
            except AsiCheckConditionError as e:
                (key, code) = (e.sense_obj.sense_key, e.sense_obj.additional_sense_code.code_name)
                if (key, code) == ('ILLEGAL_REQUEST', 'INVALID FIELD IN CDB'):
                    return
                raise

        def _get_scsi_standard_inquiry_the_right_way():
            allocation_length = STANDARD_INQUIRY_MINIMAL_DATA_LENGTH
            with self.asi_context() as asi:
                command = StandardInquiryCommand(allocation_length=allocation_length)
                result = sync_wait(command.execute(asi))
                if result.additional_length >= 0:
                    allocation_length += result.additional_length
                    command = StandardInquiryCommand(allocation_length=allocation_length)
                    result = sync_wait(command.execute(asi))
            return result

        # the correct and safe way to get all the inquiry data is to ask for the mandatory 96 bytes
        # then look at the allocation length and ask again to get the extended data
        # other tools just ask for a large allocation length; until now, we did that approach and asked for 260 bytes
        # but we did not handle the case in which is was to much and the device returned INVALID FIELD IN CDB
        # so now we first ask for a large buffer of 254 bytes like other tools, and if that doesn't work
        # then we fail-back to the safe way
        return _get_scsi_standard_inquiry_the_fastest_way() or _get_scsi_standard_inquiry_the_right_way()


class SCSICommandInformationMixin(InquiryInformationMixin):

    @check_for_scsi_errors
    def get_scsi_test_unit_ready(self):
        """Returns True if the device is ready, False if got NOT_READY check condition
        """
        from infi.asi.cdb.tur import TestUnitReadyCommand
        from infi.asi.coroutines.sync_adapter import sync_wait
        from infi.asi.errors import AsiCheckConditionError, AsiReservationConflictError
        with self.asi_context() as asi:
            try:
                command = TestUnitReadyCommand()
                return sync_wait(command.execute(asi))
            except AsiCheckConditionError as e:
                (key, code) = (e.sense_obj.sense_key, e.sense_obj.additional_sense_code.code_name)
                if key in ('NOT_READY', 'ILLEGAL_REQUEST'):
                    return False
                if (key, code) == ('UNIT_ATTENTION', 'POWER ON OCCURRED'):
                    return False
                if (key, code) == ('UNIT_ATTENTION', 'POWER ON, RESET, OR BUS DEVICE RESET OCCURRED'):
                    return False
                if (key, code) == ('UNIT_ATTENTION', 'BUS DEVICE RESET FUNCTION OCCURRED'):
                    return False
                raise
            except AsiReservationConflictError:
                return True

    @check_for_scsi_errors
    def get_rtpg(self):
        from infi.asi.cdb.rtpg import RTPGCommand
        from infi.asi.coroutines.sync_adapter import sync_wait
        command = RTPGCommand()
        with self.asi_context() as asi:
            return sync_wait(command.execute(asi))
