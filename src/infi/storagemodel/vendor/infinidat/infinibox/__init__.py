
from infi.pyutils.lazy import cached_method
from ... import VendorMultipathBlockDevice, VendorSCSIBlockDevice, VendorSCSIStorageController

from logging import getLogger
log = getLogger(__name__)

NFINIDAT_IEEE = 0x742B0F
vid_pid = ("NFINIDAT" , "Infinidat A01")

# pylint: disable=C0103
