from infi.instruct import UBInt8, UBInt16, Field, Struct
from infi.instruct.macros import VarSizeString
from infi.asi.cdb.inquiry import PeripheralDeviceData
from infi.asi.cdb.inquiry.vpd_pages import EVPDInquiryCommand

class JSONInquiryPageData(Struct):
    _fields_ = [
        Field("peripheral_device", PeripheralDeviceData),
        UBInt8("page_code"),
        VarSizeString("json_serialized_data", UBInt16)
    ]

class JSONInquiryPageCommand(EVPDInquiryCommand):
    def __init__(self):
        # pylint: disable=E1002
            # pylint: disable=E1002
        super(JSONInquiryPageCommand, self).__init__(0xc5, 1024, JSONInquiryPageData)
