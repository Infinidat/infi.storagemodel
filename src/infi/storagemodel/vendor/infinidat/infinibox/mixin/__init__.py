
from infi.pyutils.lazy import cached_method
from infi.storagemodel.vendor import VendorMultipathDevice, VendorSCSIBlockDevice, VendorSCSIStorageController

from logging import getLogger
log = getLogger()

from .inquiry import InfiniBoxInquiryMixin
from .volume import InfiniBoxVolumeMixin
from .sophisticated import SophisticatedMixin

class block_class(InfiniBoxInquiryMixin, SophisticatedMixin, InfiniBoxVolumeMixin, VendorSCSIBlockDevice):
    def __repr__(self):
        return "<Infinibox Mixin for {!r}>".format(self.device)

class controller_class(InfiniBoxInquiryMixin, SophisticatedMixin, VendorSCSIStorageController):
    def __repr__(self):
        return "<Infinibox Mixin for {!r}>".format(self.device)

class multipath_class(InfiniBoxInquiryMixin, SophisticatedMixin, InfiniBoxVolumeMixin, VendorMultipathDevice):
    def __repr__(self):
        return "<Infinibox Mixin for {!r}>".format(self.device)

