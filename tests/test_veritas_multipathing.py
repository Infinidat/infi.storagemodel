from infi.storagemodel import get_storage_model
from infi.pyutils.contexts import contextmanager
from infi.pyutils.lazy import clear_cache
from unittest import TestCase, SkipTest
from mock import Mock, patch
from os import name

VXDMPADM_OUTPUT_TEMPLATE = """dmpdev      = sda
state       = enabled
enclosure   = other_disks
cab-sno     = OTHER_DISKS
asl     = otherdisks
vid     = VMware
pid     = Virtual disk
array-name  = OTHER_DISKS
array-type  = OTHER_DISKS
iopolicy    = Balanced
avid        = -
lun-sno     =
udid        = VMware%5FVirtual%20disk%5FOTHER%5FDISKS%5Fhost-ci102.lab.il.infinidat.com%5F%2Fdev%2Fsda
dev-attr    = -
lun_type    = -
scsi3_vpd   = -
replicated  = no
num_paths   = 1
###path     = name state type transport ctlr hwpath aportID aportWWN attr
path        = sda enabled(a) - SCSI c0 c0 - - -

dmpdev      = infinibox0_0ace
state       = enabled
enclosure   = infinibox0
cab-sno     = 4e4f
asl     = libvxinfinibox.so
vid     = {vid}
pid     = {pid}
array-name  = InfiniBox
array-type  = A/A
iopolicy    = MinimumQ
avid        = 0ace
lun-sno     = 742b0f000004e4f0000000000000ace
udid        = NFINIDAT%5FInfiniBox%5F4e4f%5F742b0f000004e4f0000000000000ace
dev-attr    = tprclm
lun_type    = std
scsi3_vpd   = NAA:6742B0F000004E4F0000000000000ACE
replicated  = no
num_paths   = 6
###path     = name state type transport ctlr hwpath aportID aportWWN attr
{paths}
"""

SIX_PATHS = """path        = sdc enabled(a) - FC c3 c3 2-2 57:42:b0:f0:00:4e:4f:32 -
path        = sdn enabled(a) - FC c3 c3 2-2 57:42:b0:f0:00:4e:4f:22 -
path        = sdbf enabled(a) - FC c3 c3 1-1 57:42:b0:f0:00:4e:4f:11 -
path        = sdau enabled(a) - FC c3 c3 1-1 57:42:b0:f0:00:4e:4f:21 -
path        = sdy enabled(a) - FC c3 c3 2-2 57:42:b0:f0:00:4e:4f:12 -
path        = sdaj enabled(a) - FC c3 c3 1-1 57:42:b0:f0:00:4e:4f:31 -
"""

ALL_DISABLED = """path        = sdc disabled(a) - FC c3 c3 2-2 57:42:b0:f0:00:4e:4f:32 -
path        = sdn disabled(a) - FC c3 c3 2-2 57:42:b0:f0:00:4e:4f:22 -
path        = sdbf disabled(a) - FC c3 c3 1-1 57:42:b0:f0:00:4e:4f:11 -
path        = sdau disabled(a) - FC c3 c3 1-1 57:42:b0:f0:00:4e:4f:21 -
path        = sdy disabled(a) - FC c3 c3 2-2 57:42:b0:f0:00:4e:4f:12 -
path        = sdaj disabled(a) - FC c3 c3 1-1 57:42:b0:f0:00:4e:4f:31 -
"""

ONE_ENABLED = """path        = sdc disabled(a) - FC c3 c3 2-2 57:42:b0:f0:00:4e:4f:32 -
path        = sdn disabled(a) - FC c3 c3 2-2 57:42:b0:f0:00:4e:4f:22 -
path        = sdbf disabled(a) - FC c3 c3 1-1 57:42:b0:f0:00:4e:4f:11 -
path        = sdau disabled(a) - FC c3 c3 1-1 57:42:b0:f0:00:4e:4f:21 -
path        = sdy enabled(a) - FC c3 c3 2-2 57:42:b0:f0:00:4e:4f:12 -
path        = sdaj disabled(a) - FC c3 c3 1-1 57:42:b0:f0:00:4e:4f:31 -
"""

@contextmanager
def veritas_multipathing_context(read_paths_list_func, output):
    if name == "nt":
        raise SkipTest
    read_paths_list_func.return_value = output
    sm = get_storage_model()
    clear_cache(sm)
    yield sm.get_veritas_multipath()


class VeritasMultipathingTestCase(TestCase):
    @patch('infi.storagemodel.linux.veritas_multipath.VeritasMultipathClient.read_paths_list')
    def test_vxdmpadm_output(self, read_paths_list):
        vxdmpadm_output = VXDMPADM_OUTPUT_TEMPLATE.format(paths=SIX_PATHS, vid="NFINIDAT", pid="InfiniBox")
        with veritas_multipathing_context(read_paths_list, vxdmpadm_output) as veritas_multipath:
            block_devices = veritas_multipath.get_all_multipath_block_devices()
            self.assertEquals(len(block_devices), 1)
            self.assertEquals(len(block_devices[0].get_paths()), 6)

    @patch('infi.storagemodel.linux.veritas_multipath.VeritasMultipathClient.read_paths_list')
    def test_vxdmpadm_output_no_paths(self, read_paths_list):
        vxdmpadm_output = VXDMPADM_OUTPUT_TEMPLATE.format(paths="", vid="NFINIDAT", pid="InfiniBox")
        with veritas_multipathing_context(read_paths_list, vxdmpadm_output) as veritas_multipath:
            block_devices = veritas_multipath.get_all_multipath_block_devices()
            self.assertEquals(len(block_devices), 0)

    @patch('infi.storagemodel.linux.veritas_multipath.VeritasMultipathClient.read_paths_list')
    def test_vxdmpadm_output_all_paths_disabled(self, read_paths_list):
        vxdmpadm_output = VXDMPADM_OUTPUT_TEMPLATE.format(paths=ALL_DISABLED, vid="NFINIDAT", pid="InfiniBox")
        with veritas_multipathing_context(read_paths_list, vxdmpadm_output) as veritas_multipath:
            block_devices = veritas_multipath.get_all_multipath_block_devices()
            self.assertEquals(len(block_devices), 0)

    @patch('infi.storagemodel.linux.veritas_multipath.VeritasMultipathClient.read_paths_list')
    def test_vxdmpadm_output_one_path_enabled(self, read_paths_list):
        vxdmpadm_output = VXDMPADM_OUTPUT_TEMPLATE.format(paths=ONE_ENABLED, vid="NFINIDAT", pid="InfiniBox")
        with veritas_multipathing_context(read_paths_list, vxdmpadm_output) as veritas_multipath:
            block_devices = veritas_multipath.get_all_multipath_block_devices()
            self.assertEquals(len(block_devices), 1)
            self.assertEquals(len(block_devices[0].get_paths()), 6)
            self.assertEquals(len([p for p in block_devices[0].get_paths() if p.get_state() == "up"]), 1)

    @patch('infi.storagemodel.base.inquiry.InquiryInformationMixin.get_scsi_vendor_id_or_unknown_on_error')
    @patch('infi.storagemodel.linux.veritas_multipath.VeritasMultipathClient.read_paths_list')
    def test_vxdmpadm_output_bad_vid(self, read_paths_list, get_scsi_vendor_id_or_unknown_on_error):
        from infi.storagemodel.vendor.infinidat.shortcuts import get_infinidat_veritas_multipath_block_devices
        vid, pid = ("NFINIDAS", "InfiniBox")
        vxdmpadm_output = VXDMPADM_OUTPUT_TEMPLATE.format(paths=SIX_PATHS, vid=vid, pid=pid)
        get_scsi_vendor_id_or_unknown_on_error.return_value = vid, pid
        with veritas_multipathing_context(read_paths_list, vxdmpadm_output) as veritas_multipath:
            block_devices = get_infinidat_veritas_multipath_block_devices()
            self.assertEquals(len(block_devices), 0)

    @patch('infi.storagemodel.base.inquiry.InquiryInformationMixin.get_scsi_vendor_id_or_unknown_on_error')
    @patch('infi.storagemodel.linux.veritas_multipath.VeritasMultipathClient.read_paths_list')
    def test_vxdmpadm_output_bad_pid(self, read_paths_list, get_scsi_vendor_id_or_unknown_on_error):
        from infi.storagemodel.vendor.infinidat.shortcuts import get_infinidat_veritas_multipath_block_devices
        vid, pid = ("NFINIDAT", "InfiniBos")
        vxdmpadm_output = VXDMPADM_OUTPUT_TEMPLATE.format(paths=SIX_PATHS, vid=vid, pid=pid)
        get_scsi_vendor_id_or_unknown_on_error.return_value = (vid, pid)
        with veritas_multipathing_context(read_paths_list, vxdmpadm_output) as veritas_multipath:
            block_devices = get_infinidat_veritas_multipath_block_devices()
            self.assertEquals(len(block_devices), 0)


