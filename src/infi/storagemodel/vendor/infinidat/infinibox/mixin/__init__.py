
from infi.pyutils.lazy import cached_method
from infi.storagemodel.vendor import VendorMultipathDevice, VendorSCSIBlockDevice, VendorSCSIStorageController

from logging import getLogger
log = getLogger()

from .inquiry import InfiniBoxInquiryMixin
from .volume import InfiniBoxVolumeMixin
from .sophisticated import SophisticatedMixin

class block_class(InfiniBoxInquiryMixin, SophisticatedMixin, InfiniBoxVolumeMixin, VendorSCSIBlockDevice):
    pass

class controller_class(InfiniBoxInquiryMixin, SophisticatedMixin, VendorSCSIStorageController):
    pass

class multipath_class(InfiniBoxInquiryMixin, SophisticatedMixin, InfiniBoxVolumeMixin, VendorMultipathDevice):
    pass
