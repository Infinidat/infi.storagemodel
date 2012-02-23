
from infi.pyutils.lazy import cached_method
from infi.storagemodel.vendor import VendorMultipathDevice, VendorSCSIBlockDevice, VendorSCSIStorageController

from logging import getLogger
log = getLogger()

from .inquiry import InfiniBoxInquiryMixin
from .volume import InfiniBoxVolumeMixin
from .sophisticated import SophisticatedMixin

class block_class(InfiniBoxInquiryMixin, SophisticatedMixin, InfiniBoxVolumeMixin, VendorSCSIBlockDevice):
    def __repr__(self):
        msg = "<Block device for volume {} of system {}, mapped to host {}, address {}>"
        return msg.format(self.get_volume_id(), self.get_system_serial(),
                          self.get_host_id(), self.get_management_address())

class controller_class(InfiniBoxInquiryMixin, SophisticatedMixin, VendorSCSIStorageController):
    def __repr__(self):
        msg = "<Controller for system {}, mapped to host {}, address {} >"
        return msg.format(self.get_system_serial(), self.get_host_id(), self.get_management_address())

class multipath_class(InfiniBoxInquiryMixin, SophisticatedMixin, InfiniBoxVolumeMixin, VendorMultipathDevice):
    def __repr__(self):
        msg = "<Multipath device for volume {} of system {}, mapped to host {}, address {}>"
        return msg.format(self.get_volume_id(), self.get_system_serial(),
                          self.get_host_id(), self.get_management_address())
