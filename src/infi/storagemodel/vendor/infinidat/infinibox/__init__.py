
from infi.pyutils.lazy import cached_method
from ... import VendorMultipathDevice, VendorSCSIBlockDevice, VendorSCSIStorageController

from logging import getLogger
log = getLogger()

NFINIDAT_IEEE = 0x742B0F
vid_pid = ("NFINIDAT" , "Infinidat A01")

# pylint: disable=C0103
