
from infi.pyutils.lazy import cached_method
from ... import VendorMultipathBlockDevice, VendorSCSIBlockDevice, VendorSCSIStorageController, VendorSCSIEnclosureDevice

from logging import getLogger
log = getLogger(__name__)

NFINIDAT_IEEE = 0x742B0F
vid_pid = ("NFINIDAT" , "InfiniBox")

# pylint: disable=C0103
