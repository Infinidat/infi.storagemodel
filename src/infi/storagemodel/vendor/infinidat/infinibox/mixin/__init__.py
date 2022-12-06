from infi.storagemodel.vendor import VendorSCSIBlockDevice, VendorSCSIStorageController, VendorSCSIEnclosureDevice
from infi.storagemodel.vendor import VendorMultipathBlockDevice, VendorMultipathStorageController

from logging import getLogger
log = getLogger(__name__)

from .inquiry import InfiniBoxInquiryMixin
from .volume import InfiniBoxVolumeMixin
from .sophisticated import SophisticatedMixin


class scsi_block_class(InfiniBoxInquiryMixin, SophisticatedMixin, InfiniBoxVolumeMixin, VendorSCSIBlockDevice):
    def __repr__(self):
        return "<Infinibox Mixin for {!r}>".format(self.device)


class scsi_controller_class(InfiniBoxInquiryMixin, SophisticatedMixin, VendorSCSIStorageController):
    def __repr__(self):
        return "<Infinibox Mixin for {!r}>".format(self.device)


class scsi_enclosure_class(InfiniBoxInquiryMixin, SophisticatedMixin, VendorSCSIEnclosureDevice):
    def __repr__(self):
        return "<Infinibox Mixin for {!r}>".format(self.device)


class multipath_block_class(InfiniBoxInquiryMixin, SophisticatedMixin, InfiniBoxVolumeMixin, VendorMultipathBlockDevice):
    def __repr__(self):
        return "<Infinibox Mixin for {!r}>".format(self.device)


class multipath_controller_class(InfiniBoxInquiryMixin, SophisticatedMixin, VendorMultipathStorageController):
    def __repr__(self):
        return "<Infinibox Mixin for {!r}>".format(self.device)
