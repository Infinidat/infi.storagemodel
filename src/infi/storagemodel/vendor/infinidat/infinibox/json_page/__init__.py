from infi.instruct.buffer import Buffer, buffer_field, bytes_ref, be_uint_field, len_ref, self_ref, json_field
from infi.asi.cdb.inquiry import PeripheralDeviceDataBuffer
from infi.asi.cdb.inquiry.vpd_pages import EVPDInquiryCommand
import json

class JSONInquiryPageBuffer(Buffer):
    def _calc_json_length(self):
        import json
        return len(json.dumps(self.json_data))

    peripheral_device = buffer_field(where=bytes_ref[0:], type=PeripheralDeviceDataBuffer)
    page_code = be_uint_field(where=bytes_ref[1])
    page_length = be_uint_field(where=bytes_ref[2:4], set_before_pack=self_ref._calc_json_length())
    json_data = json_field(where=bytes_ref[4:4+page_length], unpack_after=page_length)


class JSONInquiryPageCommand(EVPDInquiryCommand):
    def __init__(self):
        # pylint: disable=E1002
            # pylint: disable=E1002
        super(JSONInquiryPageCommand, self).__init__(0xc5, 1024, JSONInquiryPageBuffer)
