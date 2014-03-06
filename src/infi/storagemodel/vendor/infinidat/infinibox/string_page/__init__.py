from infi.instruct import UBInt8, UBInt16, Field, Struct
from infi.instruct.macros import VarSizeString
from infi.asi.cdb.inquiry import PeripheralDeviceData
from infi.asi.cdb.inquiry.vpd_pages import EVPDInquiryCommand

class StringInquiryPageData(Struct):
    _fields_ = [
        Field("peripheral_device", PeripheralDeviceData),
        UBInt8("page_code"),
        VarSizeString("string", UBInt16)
    ]

class StringInquiryPageCommand(EVPDInquiryCommand):
    def __init__(self, page):
        # pylint: disable=E1002
            # pylint: disable=E1002
        super(StringInquiryPageCommand, self).__init__(page, 1024, StringInquiryPageData)
