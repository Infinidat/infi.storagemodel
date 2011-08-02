
from ..utils import cached_method
from . import VendorMultipathDevice, VendorSCSIBlockDevice, VendorSCSIStorageController

class InfiniBoxMixin(object):
    @cached_method
    def get_box_ipv4_address(self):
        return ''

class block_class(InfiniBoxMixin, VendorSCSIBlockDevice):
    pass

class controller_class(InfiniBoxMixin, VendorSCSIStorageController):
    pass

class multipath_class(InfiniBoxMixin, VendorMultipathDevice):
    pass

vid_pid = ("NFINIDAT", "InfiniBox")
