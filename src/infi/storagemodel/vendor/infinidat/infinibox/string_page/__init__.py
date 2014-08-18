from infi.instruct.buffer import Buffer, buffer_field, bytes_ref, be_uint_field, len_ref, self_ref, str_field
from infi.asi.cdb.inquiry import PeripheralDeviceDataBuffer
from infi.asi.cdb.inquiry.vpd_pages import EVPDInquiryCommand


class StringInquiryPageBuffer(Buffer):
    peripheral_device = buffer_field(where=bytes_ref[0:], type=PeripheralDeviceDataBuffer)
    page_code = be_uint_field(where=bytes_ref[1])
    page_length = be_uint_field(where=bytes_ref[2:4], set_before_pack=len_ref(self_ref.string))
    string = str_field(where=bytes_ref[4:4+page_length], unpack_after=page_length)


class StringInquiryPageCommand(EVPDInquiryCommand):
    def __init__(self, page):
        # pylint: disable=E1002
            # pylint: disable=E1002
        super(StringInquiryPageCommand, self).__init__(page, 1024, StringInquiryPageBuffer)
