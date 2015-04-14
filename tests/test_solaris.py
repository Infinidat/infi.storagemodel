from infi.storagemodel.vendor.infinidat.infinibox import vid_pid
from infi.storagemodel.linux.scsi import LinuxSCSIBlockDevice
from infi.dtypes.hctl import HCTL
from infi.storagemodel import get_storage_model
from infi.pyutils.contexts import contextmanager
from infi.pyutils.lazy import clear_cache
from unittest import TestCase, SkipTest
from mock import Mock, patch
from os import name
from infi.os_info import get_platform_string

MPATHADM_LISTLU_OUTPUT_TEMPLATE = """  /scsi_vhci/array-controller@g6742b0f0000075360000000000000000
                Total Path Count: 1
                Operational Path Count: 1
        /dev/rdsk/c0t6742B0F000007536000000000000217Dd0s2
                Total Path Count: 3
                Operational Path Count: 3
"""

MPATHADM_SHOWLU_OUTPUT_TEMPLATE = {
    '/scsi_vhci/array-controller@g6742b0f0000075360000000000000000' : """ Logical Unit:  /scsi_vhci/array-controller@g6742b0f0000075360000000000000000
        mpath-support:  libmpscsi_vhci.so
        Vendor:  NFINIDAT
        Product:  InfiniBox
        Revision:  0h
        Name Type:  unknown type
        Name:  6742b0f0000075360000000000000000
        Asymmetric:  yes
        Current Load Balance:  round-robin
        Logical Unit Group ID:  NA
        Auto Failback:  on
        Auto Probing:  NA

        Paths:
                Initiator Port Name:  10000000c9d0815c
                Target Port Name:  5742b0f000753611
                Override Path:  NA
                Path State:  OK
                Disabled:  no

        Target Port Groups:
                ID:  257
                Explicit Failover:  no
                Access State:  active optimized
                Target Ports:
                        Name:  5742b0f000753611
                        Relative ID:  257
    """,
    '/dev/rdsk/c0t6742B0F000007536000000000000217Dd0s2' : """Logical Unit:  /dev/rdsk/c0t6742B0F000007536000000000000217Dd0s2
        mpath-support:  libmpscsi_vhci.so
        Vendor:  {vid}
        Product:  {pid}
        Revision:  0h
        Name Type:  unknown type
        Name:  6742b0f000007536000000000000217d
        Asymmetric:  yes
        Current Load Balance:  round-robin
        Logical Unit Group ID:  NA
        Auto Failback:  on
        Auto Probing:  NA

        Paths:
                {paths}

        Target Port Groups:
                ID:  257
                Explicit Failover:  no
                Access State:  active optimized
                Target Ports:
                        Name:  5742b0f000753611
                        Relative ID:  257
    """,
}

MPATH_DEVICE_PATH = '/dev/rdsk/c0t6742B0F000007536000000000000217Dd0s2'

THREE_PATHS = """Initiator Port Name:  10000000c9d0815c
                Target Port Name:  5742b0f000753611
                Override Path:  NA
                Path State:  OK
                Disabled:  no

                Initiator Port Name:  10000000c9d0815c
                Target Port Name:  5742b0f000753612
                Override Path:  NA
                Path State:  OK
                Disabled:  no

                Initiator Port Name:  10000000c9d0815c
                Target Port Name:  5742b0f000753613
                Override Path:  NA
                Path State:  OK
                Disabled:  no
"""

ALL_DISABLED = """Initiator Port Name:  10000000c9d0815c
                Target Port Name:  5742b0f000753611
                Override Path:  NA
                Path State:  OK
                Disabled:  yes

                Initiator Port Name:  10000000c9d0815c
                Target Port Name:  5742b0f000753612
                Override Path:  NA
                Path State:  OK
                Disabled:  yes

                Initiator Port Name:  10000000c9d0815c
                Target Port Name:  5742b0f000753613
                Override Path:  NA
                Path State:  OK
                Disabled:  yes
"""

ALL_INACTIVE = """Initiator Port Name:  10000000c9d0815c
                Target Port Name:  5742b0f000753611
                Override Path:  NA
                Path State:  ERROR
                Disabled:  no

                Initiator Port Name:  10000000c9d0815c
                Target Port Name:  5742b0f000753612
                Override Path:  NA
                Path State:  ERROR
                Disabled:  no

                Initiator Port Name:  10000000c9d0815c
                Target Port Name:  5742b0f000753613
                Override Path:  NA
                Path State:  ERROR
                Disabled:  no
"""

ONE_ENABLED = """Initiator Port Name:  10000000c9d0815c
                Target Port Name:  5742b0f000753611
                Override Path:  NA
                Path State:  OK
                Disabled:  yes

                Initiator Port Name:  10000000c9d0815c
                Target Port Name:  5742b0f000753612
                Override Path:  NA
                Path State:  OK
                Disabled:  no

                Initiator Port Name:  10000000c9d0815c
                Target Port Name:  5742b0f000753613
                Override Path:  NA
                Path State:  OK
                Disabled:  yes
"""


class MockSCSIBlockDevice(LinuxSCSIBlockDevice):
    def get_hctl(self):
        return HCTL(1,2,3,4)


@contextmanager
def solaris_multipathing_context(listlu_output, showlu_output):
    if "solaris" not in get_platform_string():
        raise SkipTest
    with patch('infi.storagemodel.solaris.native_multipath.SolarisMultipathClient.read_multipaths_list') as read_multipaths_list:
        with patch('infi.storagemodel.solaris.native_multipath.SolarisMultipathClient.read_single_paths_list') as read_single_paths_list:
            with patch('infi.storagemodel.solaris.native_multipath.SolarisPath.get_hctl') as get_hctl:
                def side_effect(device):
                    return showlu_output[device]
                get_hctl.return_value = HCTL(1,2,3,4)
                read_multipaths_list.return_value = listlu_output
                read_single_paths_list.side_effect = side_effect
                sm = get_storage_model()
                clear_cache(sm)
                yield sm.get_native_multipath()


class SolarisMultipathingTestCase(TestCase):
    def test_mpathadm_output(self):
        vid, pid = ("NFINIDAT", "InfiniBox")
        showlu_output = dict(MPATHADM_SHOWLU_OUTPUT_TEMPLATE)
        showlu_output[MPATH_DEVICE_PATH] = showlu_output[MPATH_DEVICE_PATH].format(paths=THREE_PATHS, vid=vid, pid=pid)
        with solaris_multipathing_context(MPATHADM_LISTLU_OUTPUT_TEMPLATE, showlu_output) as solaris_multipath:
            block_devices = solaris_multipath.get_all_multipath_block_devices()
            self.assertEquals(len(block_devices), 1)
            self.assertEquals(len(block_devices[0].get_paths()), 3)
            self.assertEquals(len(solaris_multipath.filter_vendor_specific_devices(block_devices, vid_pid)), 1)

    def test_mpathadm_output_storage_ctrl(self):
        vid, pid = ("NFINIDAT", "InfiniBox")
        showlu_output = dict(MPATHADM_SHOWLU_OUTPUT_TEMPLATE)
        showlu_output[MPATH_DEVICE_PATH] = showlu_output[MPATH_DEVICE_PATH].format(paths=THREE_PATHS, vid=vid, pid=pid)
        with solaris_multipathing_context(MPATHADM_LISTLU_OUTPUT_TEMPLATE, showlu_output) as solaris_multipath:
            storage_controllers = solaris_multipath.get_all_multipath_storage_controller_devices()
            self.assertEquals(len(storage_controllers), 1)
            self.assertEquals(len(storage_controllers[0].get_paths()), 1)
            self.assertEquals(len(solaris_multipath.filter_vendor_specific_devices(storage_controllers, vid_pid)), 1)

    def test_mpathadm_output_no_paths(self):
        vid, pid = ("NFINIDAT", "InfiniBox")
        showlu_output = dict(MPATHADM_SHOWLU_OUTPUT_TEMPLATE)
        showlu_output[MPATH_DEVICE_PATH] = showlu_output[MPATH_DEVICE_PATH].format(paths="", vid=vid, pid=pid)
        with solaris_multipathing_context(MPATHADM_LISTLU_OUTPUT_TEMPLATE, showlu_output) as solaris_multipath:
            block_devices = solaris_multipath.get_all_multipath_block_devices()
            self.assertEquals(len(block_devices), 0)

    def test_mpathadm_output_all_paths_disabled(self):
        vid, pid = ("NFINIDAT", "InfiniBox")
        showlu_output = dict(MPATHADM_SHOWLU_OUTPUT_TEMPLATE)
        showlu_output[MPATH_DEVICE_PATH] = showlu_output[MPATH_DEVICE_PATH].format(paths=ALL_DISABLED, vid=vid, pid=pid)
        with solaris_multipathing_context(MPATHADM_LISTLU_OUTPUT_TEMPLATE, showlu_output) as solaris_multipath:
            block_devices = solaris_multipath.get_all_multipath_block_devices()
            self.assertEquals(len(block_devices), 0)

    def test_mpathadm_output_all_paths_incative(self):
        vid, pid = ("NFINIDAT", "InfiniBox")
        showlu_output = dict(MPATHADM_SHOWLU_OUTPUT_TEMPLATE)
        showlu_output[MPATH_DEVICE_PATH] = showlu_output[MPATH_DEVICE_PATH].format(paths=ALL_INACTIVE, vid=vid, pid=pid)
        with solaris_multipathing_context(MPATHADM_LISTLU_OUTPUT_TEMPLATE, showlu_output) as solaris_multipath:
            block_devices = solaris_multipath.get_all_multipath_block_devices()
            self.assertEquals(len(block_devices), 0)

    def test_mpathadm_output_one_path_enabled(self):
        vid, pid = ("NFINIDAT", "InfiniBox")
        showlu_output = dict(MPATHADM_SHOWLU_OUTPUT_TEMPLATE)
        showlu_output[MPATH_DEVICE_PATH] = showlu_output[MPATH_DEVICE_PATH].format(paths=ONE_ENABLED, vid=vid, pid=pid)
        with solaris_multipathing_context(MPATHADM_LISTLU_OUTPUT_TEMPLATE, showlu_output) as solaris_multipath:
            block_devices = solaris_multipath.get_all_multipath_block_devices()
            self.assertEquals(len(block_devices), 1)
            self.assertEquals(len(block_devices[0].get_paths()), 3)
            self.assertEquals(len([p for p in block_devices[0].get_paths() if p.get_state() == "up"]), 1)

    def test_mpathadm_output_bad_vid(self):
        vid, pid = ("NFINIDAS", "InfiniBox")
        showlu_output = dict(MPATHADM_SHOWLU_OUTPUT_TEMPLATE)
        showlu_output[MPATH_DEVICE_PATH] = showlu_output[MPATH_DEVICE_PATH].format(paths=ONE_ENABLED, vid=vid, pid=pid)
        with solaris_multipathing_context(MPATHADM_LISTLU_OUTPUT_TEMPLATE, showlu_output) as solaris_multipath:
            block_devices = solaris_multipath.get_all_multipath_block_devices()
            self.assertEquals(len(block_devices), 1)
            self.assertEquals(len(solaris_multipath.filter_vendor_specific_devices(block_devices, vid_pid)), 0)

    def test_mpathadm_output_bad_pid(self):
        vid, pid = ("NFINIDAT", "InfiniBot")
        showlu_output = dict(MPATHADM_SHOWLU_OUTPUT_TEMPLATE)
        showlu_output[MPATH_DEVICE_PATH] = showlu_output[MPATH_DEVICE_PATH].format(paths=ONE_ENABLED, vid=vid, pid=pid)
        with solaris_multipathing_context(MPATHADM_LISTLU_OUTPUT_TEMPLATE, showlu_output) as solaris_multipath:
            block_devices = solaris_multipath.get_all_multipath_block_devices()
            self.assertEquals(len(block_devices), 1)
            self.assertEquals(len(solaris_multipath.filter_vendor_specific_devices(block_devices, vid_pid)), 0)







class SolarisSCSITestCase(TestCase):

    def SetUp(self):
        if "solaris" not in get_platform_string():
            raise SkipTest

    @patch('infi.storagemodel.base.inquiry.InquiryInformationMixin.get_scsi_vendor_id_or_unknown_on_error', autospec=True)
    @patch('os.path.exists')
    @patch('os.readlink')
    @patch('os.listdir')
    @patch('__builtin__.open')
    def test_solaris_scsi_model(self, open_mock, listdir_mock, readlink_mock, exists_mock, get_vid_mock):
        readlink_map = {'/dev/rdsk/c3t5742B0F000753611d10p0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:q,raw',
                        '/dev/rdsk/c3t5742B0F000753611d10p1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:r,raw',
                        '/dev/rdsk/c3t5742B0F000753611d10p2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:s,raw',
                        '/dev/rdsk/c3t5742B0F000753611d10p3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:t,raw',
                        '/dev/rdsk/c3t5742B0F000753611d10p4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:u,raw',
                        '/dev/rdsk/c3t5742B0F000753611d10s0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:a,raw',
                        '/dev/rdsk/c3t5742B0F000753611d10s1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:b,raw',
                        '/dev/rdsk/c3t5742B0F000753611d10s10': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:k,raw',
                        '/dev/rdsk/c3t5742B0F000753611d10s11': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:l,raw',
                        '/dev/rdsk/c3t5742B0F000753611d10s12': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:m,raw',
                        '/dev/rdsk/c3t5742B0F000753611d10s13': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:n,raw',
                        '/dev/rdsk/c3t5742B0F000753611d10s14': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:o,raw',
                        '/dev/rdsk/c3t5742B0F000753611d10s15': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:p,raw',
                        '/dev/rdsk/c3t5742B0F000753611d10s2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:c,raw',
                        '/dev/rdsk/c3t5742B0F000753611d10s3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:d,raw',
                        '/dev/rdsk/c3t5742B0F000753611d10s4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:e,raw',
                        '/dev/rdsk/c3t5742B0F000753611d10s5': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:f,raw',
                        '/dev/rdsk/c3t5742B0F000753611d10s6': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:g,raw',
                        '/dev/rdsk/c3t5742B0F000753611d10s7': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:h,raw',
                        '/dev/rdsk/c3t5742B0F000753611d10s8': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:i,raw',
                        '/dev/rdsk/c3t5742B0F000753611d10s9': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:j,raw',
                        '/dev/rdsk/c3t5742B0F000753611d11p0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:q,raw',
                        '/dev/rdsk/c3t5742B0F000753611d11p1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:r,raw',
                        '/dev/rdsk/c3t5742B0F000753611d11p2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:s,raw',
                        '/dev/rdsk/c3t5742B0F000753611d11p3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:t,raw',
                        '/dev/rdsk/c3t5742B0F000753611d11p4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:u,raw',
                        '/dev/rdsk/c3t5742B0F000753611d11s0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:a,raw',
                        '/dev/rdsk/c3t5742B0F000753611d11s1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:b,raw',
                        '/dev/rdsk/c3t5742B0F000753611d11s10': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:k,raw',
                        '/dev/rdsk/c3t5742B0F000753611d11s11': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:l,raw',
                        '/dev/rdsk/c3t5742B0F000753611d11s12': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:m,raw',
                        '/dev/rdsk/c3t5742B0F000753611d11s13': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:n,raw',
                        '/dev/rdsk/c3t5742B0F000753611d11s14': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:o,raw',
                        '/dev/rdsk/c3t5742B0F000753611d11s15': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:p,raw',
                        '/dev/rdsk/c3t5742B0F000753611d11s2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:c,raw',
                        '/dev/rdsk/c3t5742B0F000753611d11s3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:d,raw',
                        '/dev/rdsk/c3t5742B0F000753611d11s4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:e,raw',
                        '/dev/rdsk/c3t5742B0F000753611d11s5': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:f,raw',
                        '/dev/rdsk/c3t5742B0F000753611d11s6': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:g,raw',
                        '/dev/rdsk/c3t5742B0F000753611d11s7': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:h,raw',
                        '/dev/rdsk/c3t5742B0F000753611d11s8': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:i,raw',
                        '/dev/rdsk/c3t5742B0F000753611d11s9': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:j,raw',
                        '/dev/rdsk/c3t5742B0F000753611d12p0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:q,raw',
                        '/dev/rdsk/c3t5742B0F000753611d12p1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:r,raw',
                        '/dev/rdsk/c3t5742B0F000753611d12p2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:s,raw',
                        '/dev/rdsk/c3t5742B0F000753611d12p3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:t,raw',
                        '/dev/rdsk/c3t5742B0F000753611d12p4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:u,raw',
                        '/dev/rdsk/c3t5742B0F000753611d12s0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:a,raw',
                        '/dev/rdsk/c3t5742B0F000753611d12s1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:b,raw',
                        '/dev/rdsk/c3t5742B0F000753611d12s10': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:k,raw',
                        '/dev/rdsk/c3t5742B0F000753611d12s11': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:l,raw',
                        '/dev/rdsk/c3t5742B0F000753611d12s12': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:m,raw',
                        '/dev/rdsk/c3t5742B0F000753611d12s13': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:n,raw',
                        '/dev/rdsk/c3t5742B0F000753611d12s14': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:o,raw',
                        '/dev/rdsk/c3t5742B0F000753611d12s15': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:p,raw',
                        '/dev/rdsk/c3t5742B0F000753611d12s2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:c,raw',
                        '/dev/rdsk/c3t5742B0F000753611d12s3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:d,raw',
                        '/dev/rdsk/c3t5742B0F000753611d12s4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:e,raw',
                        '/dev/rdsk/c3t5742B0F000753611d12s5': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:f,raw',
                        '/dev/rdsk/c3t5742B0F000753611d12s6': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:g,raw',
                        '/dev/rdsk/c3t5742B0F000753611d12s7': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:h,raw',
                        '/dev/rdsk/c3t5742B0F000753611d12s8': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:i,raw',
                        '/dev/rdsk/c3t5742B0F000753611d12s9': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:j,raw',
                        '/dev/rdsk/c3t5742B0F000753611d13p0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:q,raw',
                        '/dev/rdsk/c3t5742B0F000753611d13p1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:r,raw',
                        '/dev/rdsk/c3t5742B0F000753611d13p2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:s,raw',
                        '/dev/rdsk/c3t5742B0F000753611d13p3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:t,raw',
                        '/dev/rdsk/c3t5742B0F000753611d13p4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:u,raw',
                        '/dev/rdsk/c3t5742B0F000753611d13s0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:a,raw',
                        '/dev/rdsk/c3t5742B0F000753611d13s1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:b,raw',
                        '/dev/rdsk/c3t5742B0F000753611d13s10': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:k,raw',
                        '/dev/rdsk/c3t5742B0F000753611d13s11': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:l,raw',
                        '/dev/rdsk/c3t5742B0F000753611d13s12': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:m,raw',
                        '/dev/rdsk/c3t5742B0F000753611d13s13': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:n,raw',
                        '/dev/rdsk/c3t5742B0F000753611d13s14': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:o,raw',
                        '/dev/rdsk/c3t5742B0F000753611d13s15': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:p,raw',
                        '/dev/rdsk/c3t5742B0F000753611d13s2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:c,raw',
                        '/dev/rdsk/c3t5742B0F000753611d13s3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:d,raw',
                        '/dev/rdsk/c3t5742B0F000753611d13s4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:e,raw',
                        '/dev/rdsk/c3t5742B0F000753611d13s5': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:f,raw',
                        '/dev/rdsk/c3t5742B0F000753611d13s6': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:g,raw',
                        '/dev/rdsk/c3t5742B0F000753611d13s7': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:h,raw',
                        '/dev/rdsk/c3t5742B0F000753611d13s8': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:i,raw',
                        '/dev/rdsk/c3t5742B0F000753611d13s9': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:j,raw',
                        '/dev/rdsk/c3t5742B0F000753611d14p0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:q,raw',
                        '/dev/rdsk/c3t5742B0F000753611d14p1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:r,raw',
                        '/dev/rdsk/c3t5742B0F000753611d14p2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:s,raw',
                        '/dev/rdsk/c3t5742B0F000753611d14p3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:t,raw',
                        '/dev/rdsk/c3t5742B0F000753611d14p4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:u,raw',
                        '/dev/rdsk/c3t5742B0F000753611d14s0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:a,raw',
                        '/dev/rdsk/c3t5742B0F000753611d14s1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:b,raw',
                        '/dev/rdsk/c3t5742B0F000753611d14s10': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:k,raw',
                        '/dev/rdsk/c3t5742B0F000753611d14s11': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:l,raw',
                        '/dev/rdsk/c3t5742B0F000753611d14s12': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:m,raw',
                        '/dev/rdsk/c3t5742B0F000753611d14s13': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:n,raw',
                        '/dev/rdsk/c3t5742B0F000753611d14s14': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:o,raw',
                        '/dev/rdsk/c3t5742B0F000753611d14s15': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:p,raw',
                        '/dev/rdsk/c3t5742B0F000753611d14s2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:c,raw',
                        '/dev/rdsk/c3t5742B0F000753611d14s3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:d,raw',
                        '/dev/rdsk/c3t5742B0F000753611d14s4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:e,raw',
                        '/dev/rdsk/c3t5742B0F000753611d14s5': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:f,raw',
                        '/dev/rdsk/c3t5742B0F000753611d14s6': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:g,raw',
                        '/dev/rdsk/c3t5742B0F000753611d14s7': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:h,raw',
                        '/dev/rdsk/c3t5742B0F000753611d14s8': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:i,raw',
                        '/dev/rdsk/c3t5742B0F000753611d14s9': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:j,raw',
                        '/dev/rdsk/c3t5742B0F000753611d15p0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:q,raw',
                        '/dev/rdsk/c3t5742B0F000753611d15p1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:r,raw',
                        '/dev/rdsk/c3t5742B0F000753611d15p2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:s,raw',
                        '/dev/rdsk/c3t5742B0F000753611d15p3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:t,raw',
                        '/dev/rdsk/c3t5742B0F000753611d15p4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:u,raw',
                        '/dev/rdsk/c3t5742B0F000753611d15s0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:a,raw',
                        '/dev/rdsk/c3t5742B0F000753611d15s1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:b,raw',
                        '/dev/rdsk/c3t5742B0F000753611d15s10': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:k,raw',
                        '/dev/rdsk/c3t5742B0F000753611d15s11': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:l,raw',
                        '/dev/rdsk/c3t5742B0F000753611d15s12': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:m,raw',
                        '/dev/rdsk/c3t5742B0F000753611d15s13': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:n,raw',
                        '/dev/rdsk/c3t5742B0F000753611d15s14': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:o,raw',
                        '/dev/rdsk/c3t5742B0F000753611d15s15': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:p,raw',
                        '/dev/rdsk/c3t5742B0F000753611d15s2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:c,raw',
                        '/dev/rdsk/c3t5742B0F000753611d15s3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:d,raw',
                        '/dev/rdsk/c3t5742B0F000753611d15s4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:e,raw',
                        '/dev/rdsk/c3t5742B0F000753611d15s5': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:f,raw',
                        '/dev/rdsk/c3t5742B0F000753611d15s6': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:g,raw',
                        '/dev/rdsk/c3t5742B0F000753611d15s7': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:h,raw',
                        '/dev/rdsk/c3t5742B0F000753611d15s8': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:i,raw',
                        '/dev/rdsk/c3t5742B0F000753611d15s9': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:j,raw',
                        '/dev/rdsk/c3t5742B0F000753611d16p0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:q,raw',
                        '/dev/rdsk/c3t5742B0F000753611d16p1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:r,raw',
                        '/dev/rdsk/c3t5742B0F000753611d16p2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:s,raw',
                        '/dev/rdsk/c3t5742B0F000753611d16p3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:t,raw',
                        '/dev/rdsk/c3t5742B0F000753611d16p4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:u,raw',
                        '/dev/rdsk/c3t5742B0F000753611d16s0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:a,raw',
                        '/dev/rdsk/c3t5742B0F000753611d16s1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:b,raw',
                        '/dev/rdsk/c3t5742B0F000753611d16s10': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:k,raw',
                        '/dev/rdsk/c3t5742B0F000753611d16s11': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:l,raw',
                        '/dev/rdsk/c3t5742B0F000753611d16s12': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:m,raw',
                        '/dev/rdsk/c3t5742B0F000753611d16s13': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:n,raw',
                        '/dev/rdsk/c3t5742B0F000753611d16s14': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:o,raw',
                        '/dev/rdsk/c3t5742B0F000753611d16s15': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:p,raw',
                        '/dev/rdsk/c3t5742B0F000753611d16s2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:c,raw',
                        '/dev/rdsk/c3t5742B0F000753611d16s3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:d,raw',
                        '/dev/rdsk/c3t5742B0F000753611d16s4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:e,raw',
                        '/dev/rdsk/c3t5742B0F000753611d16s5': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:f,raw',
                        '/dev/rdsk/c3t5742B0F000753611d16s6': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:g,raw',
                        '/dev/rdsk/c3t5742B0F000753611d16s7': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:h,raw',
                        '/dev/rdsk/c3t5742B0F000753611d16s8': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:i,raw',
                        '/dev/rdsk/c3t5742B0F000753611d16s9': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:j,raw',
                        '/dev/rdsk/c3t5742B0F000753611d17p0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:q,raw',
                        '/dev/rdsk/c3t5742B0F000753611d17p1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:r,raw',
                        '/dev/rdsk/c3t5742B0F000753611d17p2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:s,raw',
                        '/dev/rdsk/c3t5742B0F000753611d17p3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:t,raw',
                        '/dev/rdsk/c3t5742B0F000753611d17p4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:u,raw',
                        '/dev/rdsk/c3t5742B0F000753611d17s0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:a,raw',
                        '/dev/rdsk/c3t5742B0F000753611d17s1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:b,raw',
                        '/dev/rdsk/c3t5742B0F000753611d17s10': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:k,raw',
                        '/dev/rdsk/c3t5742B0F000753611d17s11': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:l,raw',
                        '/dev/rdsk/c3t5742B0F000753611d17s12': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:m,raw',
                        '/dev/rdsk/c3t5742B0F000753611d17s13': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:n,raw',
                        '/dev/rdsk/c3t5742B0F000753611d17s14': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:o,raw',
                        '/dev/rdsk/c3t5742B0F000753611d17s15': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:p,raw',
                        '/dev/rdsk/c3t5742B0F000753611d17s2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:c,raw',
                        '/dev/rdsk/c3t5742B0F000753611d17s3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:d,raw',
                        '/dev/rdsk/c3t5742B0F000753611d17s4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:e,raw',
                        '/dev/rdsk/c3t5742B0F000753611d17s5': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:f,raw',
                        '/dev/rdsk/c3t5742B0F000753611d17s6': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:g,raw',
                        '/dev/rdsk/c3t5742B0F000753611d17s7': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:h,raw',
                        '/dev/rdsk/c3t5742B0F000753611d17s8': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:i,raw',
                        '/dev/rdsk/c3t5742B0F000753611d17s9': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:j,raw',
                        '/dev/rdsk/c3t5742B0F000753611d18p0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:q,raw',
                        '/dev/rdsk/c3t5742B0F000753611d18p1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:r,raw',
                        '/dev/rdsk/c3t5742B0F000753611d18p2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:s,raw',
                        '/dev/rdsk/c3t5742B0F000753611d18p3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:t,raw',
                        '/dev/rdsk/c3t5742B0F000753611d18p4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:u,raw',
                        '/dev/rdsk/c3t5742B0F000753611d18s0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:a,raw',
                        '/dev/rdsk/c3t5742B0F000753611d18s1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:b,raw',
                        '/dev/rdsk/c3t5742B0F000753611d18s10': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:k,raw',
                        '/dev/rdsk/c3t5742B0F000753611d18s11': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:l,raw',
                        '/dev/rdsk/c3t5742B0F000753611d18s12': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:m,raw',
                        '/dev/rdsk/c3t5742B0F000753611d18s13': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:n,raw',
                        '/dev/rdsk/c3t5742B0F000753611d18s14': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:o,raw',
                        '/dev/rdsk/c3t5742B0F000753611d18s15': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:p,raw',
                        '/dev/rdsk/c3t5742B0F000753611d18s2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:c,raw',
                        '/dev/rdsk/c3t5742B0F000753611d18s3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:d,raw',
                        '/dev/rdsk/c3t5742B0F000753611d18s4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:e,raw',
                        '/dev/rdsk/c3t5742B0F000753611d18s5': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:f,raw',
                        '/dev/rdsk/c3t5742B0F000753611d18s6': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:g,raw',
                        '/dev/rdsk/c3t5742B0F000753611d18s7': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:h,raw',
                        '/dev/rdsk/c3t5742B0F000753611d18s8': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:i,raw',
                        '/dev/rdsk/c3t5742B0F000753611d18s9': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:j,raw',
                        '/dev/rdsk/c3t5742B0F000753611d19p0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:q,raw',
                        '/dev/rdsk/c3t5742B0F000753611d19p1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:r,raw',
                        '/dev/rdsk/c3t5742B0F000753611d19p2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:s,raw',
                        '/dev/rdsk/c3t5742B0F000753611d19p3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:t,raw',
                        '/dev/rdsk/c3t5742B0F000753611d19p4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:u,raw',
                        '/dev/rdsk/c3t5742B0F000753611d19s0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:a,raw',
                        '/dev/rdsk/c3t5742B0F000753611d19s1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:b,raw',
                        '/dev/rdsk/c3t5742B0F000753611d19s10': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:k,raw',
                        '/dev/rdsk/c3t5742B0F000753611d19s11': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:l,raw',
                        '/dev/rdsk/c3t5742B0F000753611d19s12': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:m,raw',
                        '/dev/rdsk/c3t5742B0F000753611d19s13': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:n,raw',
                        '/dev/rdsk/c3t5742B0F000753611d19s14': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:o,raw',
                        '/dev/rdsk/c3t5742B0F000753611d19s15': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:p,raw',
                        '/dev/rdsk/c3t5742B0F000753611d19s2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:c,raw',
                        '/dev/rdsk/c3t5742B0F000753611d19s3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:d,raw',
                        '/dev/rdsk/c3t5742B0F000753611d19s4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:e,raw',
                        '/dev/rdsk/c3t5742B0F000753611d19s5': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:f,raw',
                        '/dev/rdsk/c3t5742B0F000753611d19s6': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:g,raw',
                        '/dev/rdsk/c3t5742B0F000753611d19s7': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:h,raw',
                        '/dev/rdsk/c3t5742B0F000753611d19s8': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:i,raw',
                        '/dev/rdsk/c3t5742B0F000753611d19s9': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:j,raw',
                        '/dev/rdsk/c3t5742B0F000753611d1p0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:q,raw',
                        '/dev/rdsk/c3t5742B0F000753611d1p1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:r,raw',
                        '/dev/rdsk/c3t5742B0F000753611d1p2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:s,raw',
                        '/dev/rdsk/c3t5742B0F000753611d1p3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:t,raw',
                        '/dev/rdsk/c3t5742B0F000753611d1p4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:u,raw',
                        '/dev/rdsk/c3t5742B0F000753611d1s0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:a,raw',
                        '/dev/rdsk/c3t5742B0F000753611d1s1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:b,raw',
                        '/dev/rdsk/c3t5742B0F000753611d1s10': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:k,raw',
                        '/dev/rdsk/c3t5742B0F000753611d1s11': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:l,raw',
                        '/dev/rdsk/c3t5742B0F000753611d1s12': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:m,raw',
                        '/dev/rdsk/c3t5742B0F000753611d1s13': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:n,raw',
                        '/dev/rdsk/c3t5742B0F000753611d1s14': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:o,raw',
                        '/dev/rdsk/c3t5742B0F000753611d1s15': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:p,raw',
                        '/dev/rdsk/c3t5742B0F000753611d1s2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:c,raw',
                        '/dev/rdsk/c3t5742B0F000753611d1s3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:d,raw',
                        '/dev/rdsk/c3t5742B0F000753611d1s4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:e,raw',
                        '/dev/rdsk/c3t5742B0F000753611d1s5': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:f,raw',
                        '/dev/rdsk/c3t5742B0F000753611d1s6': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:g,raw',
                        '/dev/rdsk/c3t5742B0F000753611d1s7': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:h,raw',
                        '/dev/rdsk/c3t5742B0F000753611d1s8': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:i,raw',
                        '/dev/rdsk/c3t5742B0F000753611d1s9': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:j,raw',
                        '/dev/rdsk/c3t5742B0F000753611d20p0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:q,raw',
                        '/dev/rdsk/c3t5742B0F000753611d20p1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:r,raw',
                        '/dev/rdsk/c3t5742B0F000753611d20p2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:s,raw',
                        '/dev/rdsk/c3t5742B0F000753611d20p3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:t,raw',
                        '/dev/rdsk/c3t5742B0F000753611d20p4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:u,raw',
                        '/dev/rdsk/c3t5742B0F000753611d20s0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:a,raw',
                        '/dev/rdsk/c3t5742B0F000753611d20s1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:b,raw',
                        '/dev/rdsk/c3t5742B0F000753611d20s10': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:k,raw',
                        '/dev/rdsk/c3t5742B0F000753611d20s11': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:l,raw',
                        '/dev/rdsk/c3t5742B0F000753611d20s12': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:m,raw',
                        '/dev/rdsk/c3t5742B0F000753611d20s13': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:n,raw',
                        '/dev/rdsk/c3t5742B0F000753611d20s14': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:o,raw',
                        '/dev/rdsk/c3t5742B0F000753611d20s15': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:p,raw',
                        '/dev/rdsk/c3t5742B0F000753611d20s2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:c,raw',
                        '/dev/rdsk/c3t5742B0F000753611d20s3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:d,raw',
                        '/dev/rdsk/c3t5742B0F000753611d20s4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:e,raw',
                        '/dev/rdsk/c3t5742B0F000753611d20s5': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:f,raw',
                        '/dev/rdsk/c3t5742B0F000753611d20s6': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:g,raw',
                        '/dev/rdsk/c3t5742B0F000753611d20s7': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:h,raw',
                        '/dev/rdsk/c3t5742B0F000753611d20s8': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:i,raw',
                        '/dev/rdsk/c3t5742B0F000753611d20s9': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:j,raw',
                        '/dev/rdsk/c3t5742B0F000753611d2p0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:q,raw',
                        '/dev/rdsk/c3t5742B0F000753611d2p1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:r,raw',
                        '/dev/rdsk/c3t5742B0F000753611d2p2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:s,raw',
                        '/dev/rdsk/c3t5742B0F000753611d2p3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:t,raw',
                        '/dev/rdsk/c3t5742B0F000753611d2p4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:u,raw',
                        '/dev/rdsk/c3t5742B0F000753611d2s0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:a,raw',
                        '/dev/rdsk/c3t5742B0F000753611d2s1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:b,raw',
                        '/dev/rdsk/c3t5742B0F000753611d2s10': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:k,raw',
                        '/dev/rdsk/c3t5742B0F000753611d2s11': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:l,raw',
                        '/dev/rdsk/c3t5742B0F000753611d2s12': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:m,raw',
                        '/dev/rdsk/c3t5742B0F000753611d2s13': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:n,raw',
                        '/dev/rdsk/c3t5742B0F000753611d2s14': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:o,raw',
                        '/dev/rdsk/c3t5742B0F000753611d2s15': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:p,raw',
                        '/dev/rdsk/c3t5742B0F000753611d2s2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:c,raw',
                        '/dev/rdsk/c3t5742B0F000753611d2s3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:d,raw',
                        '/dev/rdsk/c3t5742B0F000753611d2s4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:e,raw',
                        '/dev/rdsk/c3t5742B0F000753611d2s5': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:f,raw',
                        '/dev/rdsk/c3t5742B0F000753611d2s6': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:g,raw',
                        '/dev/rdsk/c3t5742B0F000753611d2s7': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:h,raw',
                        '/dev/rdsk/c3t5742B0F000753611d2s8': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:i,raw',
                        '/dev/rdsk/c3t5742B0F000753611d2s9': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:j,raw',
                        '/dev/rdsk/c3t5742B0F000753611d3p0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:q,raw',
                        '/dev/rdsk/c3t5742B0F000753611d3p1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:r,raw',
                        '/dev/rdsk/c3t5742B0F000753611d3p2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:s,raw',
                        '/dev/rdsk/c3t5742B0F000753611d3p3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:t,raw',
                        '/dev/rdsk/c3t5742B0F000753611d3p4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:u,raw',
                        '/dev/rdsk/c3t5742B0F000753611d3s0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:a,raw',
                        '/dev/rdsk/c3t5742B0F000753611d3s1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:b,raw',
                        '/dev/rdsk/c3t5742B0F000753611d3s10': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:k,raw',
                        '/dev/rdsk/c3t5742B0F000753611d3s11': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:l,raw',
                        '/dev/rdsk/c3t5742B0F000753611d3s12': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:m,raw',
                        '/dev/rdsk/c3t5742B0F000753611d3s13': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:n,raw',
                        '/dev/rdsk/c3t5742B0F000753611d3s14': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:o,raw',
                        '/dev/rdsk/c3t5742B0F000753611d3s15': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:p,raw',
                        '/dev/rdsk/c3t5742B0F000753611d3s2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:c,raw',
                        '/dev/rdsk/c3t5742B0F000753611d3s3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:d,raw',
                        '/dev/rdsk/c3t5742B0F000753611d3s4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:e,raw',
                        '/dev/rdsk/c3t5742B0F000753611d3s5': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:f,raw',
                        '/dev/rdsk/c3t5742B0F000753611d3s6': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:g,raw',
                        '/dev/rdsk/c3t5742B0F000753611d3s7': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:h,raw',
                        '/dev/rdsk/c3t5742B0F000753611d3s8': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:i,raw',
                        '/dev/rdsk/c3t5742B0F000753611d3s9': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:j,raw',
                        '/dev/rdsk/c3t5742B0F000753611d4p0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:q,raw',
                        '/dev/rdsk/c3t5742B0F000753611d4p1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:r,raw',
                        '/dev/rdsk/c3t5742B0F000753611d4p2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:s,raw',
                        '/dev/rdsk/c3t5742B0F000753611d4p3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:t,raw',
                        '/dev/rdsk/c3t5742B0F000753611d4p4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:u,raw',
                        '/dev/rdsk/c3t5742B0F000753611d4s0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:a,raw',
                        '/dev/rdsk/c3t5742B0F000753611d4s1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:b,raw',
                        '/dev/rdsk/c3t5742B0F000753611d4s10': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:k,raw',
                        '/dev/rdsk/c3t5742B0F000753611d4s11': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:l,raw',
                        '/dev/rdsk/c3t5742B0F000753611d4s12': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:m,raw',
                        '/dev/rdsk/c3t5742B0F000753611d4s13': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:n,raw',
                        '/dev/rdsk/c3t5742B0F000753611d4s14': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:o,raw',
                        '/dev/rdsk/c3t5742B0F000753611d4s15': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:p,raw',
                        '/dev/rdsk/c3t5742B0F000753611d4s2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:c,raw',
                        '/dev/rdsk/c3t5742B0F000753611d4s3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:d,raw',
                        '/dev/rdsk/c3t5742B0F000753611d4s4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:e,raw',
                        '/dev/rdsk/c3t5742B0F000753611d4s5': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:f,raw',
                        '/dev/rdsk/c3t5742B0F000753611d4s6': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:g,raw',
                        '/dev/rdsk/c3t5742B0F000753611d4s7': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:h,raw',
                        '/dev/rdsk/c3t5742B0F000753611d4s8': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:i,raw',
                        '/dev/rdsk/c3t5742B0F000753611d4s9': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:j,raw',
                        '/dev/rdsk/c3t5742B0F000753611d5p0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:q,raw',
                        '/dev/rdsk/c3t5742B0F000753611d5p1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:r,raw',
                        '/dev/rdsk/c3t5742B0F000753611d5p2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:s,raw',
                        '/dev/rdsk/c3t5742B0F000753611d5p3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:t,raw',
                        '/dev/rdsk/c3t5742B0F000753611d5p4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:u,raw',
                        '/dev/rdsk/c3t5742B0F000753611d5s0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:a,raw',
                        '/dev/rdsk/c3t5742B0F000753611d5s1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:b,raw',
                        '/dev/rdsk/c3t5742B0F000753611d5s10': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:k,raw',
                        '/dev/rdsk/c3t5742B0F000753611d5s11': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:l,raw',
                        '/dev/rdsk/c3t5742B0F000753611d5s12': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:m,raw',
                        '/dev/rdsk/c3t5742B0F000753611d5s13': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:n,raw',
                        '/dev/rdsk/c3t5742B0F000753611d5s14': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:o,raw',
                        '/dev/rdsk/c3t5742B0F000753611d5s15': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:p,raw',
                        '/dev/rdsk/c3t5742B0F000753611d5s2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:c,raw',
                        '/dev/rdsk/c3t5742B0F000753611d5s3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:d,raw',
                        '/dev/rdsk/c3t5742B0F000753611d5s4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:e,raw',
                        '/dev/rdsk/c3t5742B0F000753611d5s5': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:f,raw',
                        '/dev/rdsk/c3t5742B0F000753611d5s6': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:g,raw',
                        '/dev/rdsk/c3t5742B0F000753611d5s7': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:h,raw',
                        '/dev/rdsk/c3t5742B0F000753611d5s8': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:i,raw',
                        '/dev/rdsk/c3t5742B0F000753611d5s9': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:j,raw',
                        '/dev/rdsk/c3t5742B0F000753611d6p0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:q,raw',
                        '/dev/rdsk/c3t5742B0F000753611d6p1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:r,raw',
                        '/dev/rdsk/c3t5742B0F000753611d6p2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:s,raw',
                        '/dev/rdsk/c3t5742B0F000753611d6p3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:t,raw',
                        '/dev/rdsk/c3t5742B0F000753611d6p4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:u,raw',
                        '/dev/rdsk/c3t5742B0F000753611d6s0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:a,raw',
                        '/dev/rdsk/c3t5742B0F000753611d6s1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:b,raw',
                        '/dev/rdsk/c3t5742B0F000753611d6s10': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:k,raw',
                        '/dev/rdsk/c3t5742B0F000753611d6s11': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:l,raw',
                        '/dev/rdsk/c3t5742B0F000753611d6s12': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:m,raw',
                        '/dev/rdsk/c3t5742B0F000753611d6s13': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:n,raw',
                        '/dev/rdsk/c3t5742B0F000753611d6s14': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:o,raw',
                        '/dev/rdsk/c3t5742B0F000753611d6s15': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:p,raw',
                        '/dev/rdsk/c3t5742B0F000753611d6s2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:c,raw',
                        '/dev/rdsk/c3t5742B0F000753611d6s3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:d,raw',
                        '/dev/rdsk/c3t5742B0F000753611d6s4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:e,raw',
                        '/dev/rdsk/c3t5742B0F000753611d6s5': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:f,raw',
                        '/dev/rdsk/c3t5742B0F000753611d6s6': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:g,raw',
                        '/dev/rdsk/c3t5742B0F000753611d6s7': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:h,raw',
                        '/dev/rdsk/c3t5742B0F000753611d6s8': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:i,raw',
                        '/dev/rdsk/c3t5742B0F000753611d6s9': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:j,raw',
                        '/dev/rdsk/c3t5742B0F000753611d7p0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:q,raw',
                        '/dev/rdsk/c3t5742B0F000753611d7p1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:r,raw',
                        '/dev/rdsk/c3t5742B0F000753611d7p2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:s,raw',
                        '/dev/rdsk/c3t5742B0F000753611d7p3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:t,raw',
                        '/dev/rdsk/c3t5742B0F000753611d7p4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:u,raw',
                        '/dev/rdsk/c3t5742B0F000753611d7s0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:a,raw',
                        '/dev/rdsk/c3t5742B0F000753611d7s1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:b,raw',
                        '/dev/rdsk/c3t5742B0F000753611d7s10': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:k,raw',
                        '/dev/rdsk/c3t5742B0F000753611d7s11': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:l,raw',
                        '/dev/rdsk/c3t5742B0F000753611d7s12': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:m,raw',
                        '/dev/rdsk/c3t5742B0F000753611d7s13': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:n,raw',
                        '/dev/rdsk/c3t5742B0F000753611d7s14': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:o,raw',
                        '/dev/rdsk/c3t5742B0F000753611d7s15': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:p,raw',
                        '/dev/rdsk/c3t5742B0F000753611d7s2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:c,raw',
                        '/dev/rdsk/c3t5742B0F000753611d7s3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:d,raw',
                        '/dev/rdsk/c3t5742B0F000753611d7s4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:e,raw',
                        '/dev/rdsk/c3t5742B0F000753611d7s5': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:f,raw',
                        '/dev/rdsk/c3t5742B0F000753611d7s6': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:g,raw',
                        '/dev/rdsk/c3t5742B0F000753611d7s7': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:h,raw',
                        '/dev/rdsk/c3t5742B0F000753611d7s8': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:i,raw',
                        '/dev/rdsk/c3t5742B0F000753611d7s9': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:j,raw',
                        '/dev/rdsk/c3t5742B0F000753611d8p0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:q,raw',
                        '/dev/rdsk/c3t5742B0F000753611d8p1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:r,raw',
                        '/dev/rdsk/c3t5742B0F000753611d8p2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:s,raw',
                        '/dev/rdsk/c3t5742B0F000753611d8p3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:t,raw',
                        '/dev/rdsk/c3t5742B0F000753611d8p4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:u,raw',
                        '/dev/rdsk/c3t5742B0F000753611d8s0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:a,raw',
                        '/dev/rdsk/c3t5742B0F000753611d8s1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:b,raw',
                        '/dev/rdsk/c3t5742B0F000753611d8s10': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:k,raw',
                        '/dev/rdsk/c3t5742B0F000753611d8s11': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:l,raw',
                        '/dev/rdsk/c3t5742B0F000753611d8s12': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:m,raw',
                        '/dev/rdsk/c3t5742B0F000753611d8s13': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:n,raw',
                        '/dev/rdsk/c3t5742B0F000753611d8s14': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:o,raw',
                        '/dev/rdsk/c3t5742B0F000753611d8s15': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:p,raw',
                        '/dev/rdsk/c3t5742B0F000753611d8s2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:c,raw',
                        '/dev/rdsk/c3t5742B0F000753611d8s3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:d,raw',
                        '/dev/rdsk/c3t5742B0F000753611d8s4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:e,raw',
                        '/dev/rdsk/c3t5742B0F000753611d8s5': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:f,raw',
                        '/dev/rdsk/c3t5742B0F000753611d8s6': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:g,raw',
                        '/dev/rdsk/c3t5742B0F000753611d8s7': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:h,raw',
                        '/dev/rdsk/c3t5742B0F000753611d8s8': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:i,raw',
                        '/dev/rdsk/c3t5742B0F000753611d8s9': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:j,raw',
                        '/dev/rdsk/c3t5742B0F000753611d9p0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:q,raw',
                        '/dev/rdsk/c3t5742B0F000753611d9p1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:r,raw',
                        '/dev/rdsk/c3t5742B0F000753611d9p2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:s,raw',
                        '/dev/rdsk/c3t5742B0F000753611d9p3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:t,raw',
                        '/dev/rdsk/c3t5742B0F000753611d9p4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:u,raw',
                        '/dev/rdsk/c3t5742B0F000753611d9s0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:a,raw',
                        '/dev/rdsk/c3t5742B0F000753611d9s1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:b,raw',
                        '/dev/rdsk/c3t5742B0F000753611d9s10': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:k,raw',
                        '/dev/rdsk/c3t5742B0F000753611d9s11': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:l,raw',
                        '/dev/rdsk/c3t5742B0F000753611d9s12': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:m,raw',
                        '/dev/rdsk/c3t5742B0F000753611d9s13': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:n,raw',
                        '/dev/rdsk/c3t5742B0F000753611d9s14': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:o,raw',
                        '/dev/rdsk/c3t5742B0F000753611d9s15': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:p,raw',
                        '/dev/rdsk/c3t5742B0F000753611d9s2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:c,raw',
                        '/dev/rdsk/c3t5742B0F000753611d9s3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:d,raw',
                        '/dev/rdsk/c3t5742B0F000753611d9s4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:e,raw',
                        '/dev/rdsk/c3t5742B0F000753611d9s5': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:f,raw',
                        '/dev/rdsk/c3t5742B0F000753611d9s6': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:g,raw',
                        '/dev/rdsk/c3t5742B0F000753611d9s7': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:h,raw',
                        '/dev/rdsk/c3t5742B0F000753611d9s8': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:i,raw',
                        '/dev/rdsk/c3t5742B0F000753611d9s9': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:j,raw',

                        '/dev/dsk/c3t5742B0F000753611d10p0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:q',
                        '/dev/dsk/c3t5742B0F000753611d10p1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:r',
                        '/dev/dsk/c3t5742B0F000753611d10p2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:s',
                        '/dev/dsk/c3t5742B0F000753611d10p3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:t',
                        '/dev/dsk/c3t5742B0F000753611d10p4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:u',
                        '/dev/dsk/c3t5742B0F000753611d10s0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:a',
                        '/dev/dsk/c3t5742B0F000753611d10s1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:b',
                        '/dev/dsk/c3t5742B0F000753611d10s10': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:k',
                        '/dev/dsk/c3t5742B0F000753611d10s11': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:l',
                        '/dev/dsk/c3t5742B0F000753611d10s12': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:m',
                        '/dev/dsk/c3t5742B0F000753611d10s13': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:n',
                        '/dev/dsk/c3t5742B0F000753611d10s14': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:o',
                        '/dev/dsk/c3t5742B0F000753611d10s15': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:p',
                        '/dev/dsk/c3t5742B0F000753611d10s2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:c',
                        '/dev/dsk/c3t5742B0F000753611d10s3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:d',
                        '/dev/dsk/c3t5742B0F000753611d10s4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:e',
                        '/dev/dsk/c3t5742B0F000753611d10s5': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:f',
                        '/dev/dsk/c3t5742B0F000753611d10s6': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:g',
                        '/dev/dsk/c3t5742B0F000753611d10s7': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:h',
                        '/dev/dsk/c3t5742B0F000753611d10s8': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:i',
                        '/dev/dsk/c3t5742B0F000753611d10s9': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a:j',
                        '/dev/dsk/c3t5742B0F000753611d11p0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:q',
                        '/dev/dsk/c3t5742B0F000753611d11p1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:r',
                        '/dev/dsk/c3t5742B0F000753611d11p2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:s',
                        '/dev/dsk/c3t5742B0F000753611d11p3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:t',
                        '/dev/dsk/c3t5742B0F000753611d11p4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:u',
                        '/dev/dsk/c3t5742B0F000753611d11s0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:a',
                        '/dev/dsk/c3t5742B0F000753611d11s1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:b',
                        '/dev/dsk/c3t5742B0F000753611d11s10': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:k',
                        '/dev/dsk/c3t5742B0F000753611d11s11': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:l',
                        '/dev/dsk/c3t5742B0F000753611d11s12': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:m',
                        '/dev/dsk/c3t5742B0F000753611d11s13': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:n',
                        '/dev/dsk/c3t5742B0F000753611d11s14': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:o',
                        '/dev/dsk/c3t5742B0F000753611d11s15': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:p',
                        '/dev/dsk/c3t5742B0F000753611d11s2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:c',
                        '/dev/dsk/c3t5742B0F000753611d11s3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:d',
                        '/dev/dsk/c3t5742B0F000753611d11s4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:e',
                        '/dev/dsk/c3t5742B0F000753611d11s5': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:f',
                        '/dev/dsk/c3t5742B0F000753611d11s6': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:g',
                        '/dev/dsk/c3t5742B0F000753611d11s7': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:h',
                        '/dev/dsk/c3t5742B0F000753611d11s8': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:i',
                        '/dev/dsk/c3t5742B0F000753611d11s9': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b:j',
                        '/dev/dsk/c3t5742B0F000753611d12p0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:q',
                        '/dev/dsk/c3t5742B0F000753611d12p1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:r',
                        '/dev/dsk/c3t5742B0F000753611d12p2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:s',
                        '/dev/dsk/c3t5742B0F000753611d12p3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:t',
                        '/dev/dsk/c3t5742B0F000753611d12p4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:u',
                        '/dev/dsk/c3t5742B0F000753611d12s0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:a',
                        '/dev/dsk/c3t5742B0F000753611d12s1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:b',
                        '/dev/dsk/c3t5742B0F000753611d12s10': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:k',
                        '/dev/dsk/c3t5742B0F000753611d12s11': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:l',
                        '/dev/dsk/c3t5742B0F000753611d12s12': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:m',
                        '/dev/dsk/c3t5742B0F000753611d12s13': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:n',
                        '/dev/dsk/c3t5742B0F000753611d12s14': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:o',
                        '/dev/dsk/c3t5742B0F000753611d12s15': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:p',
                        '/dev/dsk/c3t5742B0F000753611d12s2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:c',
                        '/dev/dsk/c3t5742B0F000753611d12s3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:d',
                        '/dev/dsk/c3t5742B0F000753611d12s4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:e',
                        '/dev/dsk/c3t5742B0F000753611d12s5': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:f',
                        '/dev/dsk/c3t5742B0F000753611d12s6': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:g',
                        '/dev/dsk/c3t5742B0F000753611d12s7': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:h',
                        '/dev/dsk/c3t5742B0F000753611d12s8': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:i',
                        '/dev/dsk/c3t5742B0F000753611d12s9': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c:j',
                        '/dev/dsk/c3t5742B0F000753611d13p0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:q',
                        '/dev/dsk/c3t5742B0F000753611d13p1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:r',
                        '/dev/dsk/c3t5742B0F000753611d13p2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:s',
                        '/dev/dsk/c3t5742B0F000753611d13p3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:t',
                        '/dev/dsk/c3t5742B0F000753611d13p4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:u',
                        '/dev/dsk/c3t5742B0F000753611d13s0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:a',
                        '/dev/dsk/c3t5742B0F000753611d13s1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:b',
                        '/dev/dsk/c3t5742B0F000753611d13s10': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:k',
                        '/dev/dsk/c3t5742B0F000753611d13s11': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:l',
                        '/dev/dsk/c3t5742B0F000753611d13s12': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:m',
                        '/dev/dsk/c3t5742B0F000753611d13s13': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:n',
                        '/dev/dsk/c3t5742B0F000753611d13s14': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:o',
                        '/dev/dsk/c3t5742B0F000753611d13s15': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:p',
                        '/dev/dsk/c3t5742B0F000753611d13s2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:c',
                        '/dev/dsk/c3t5742B0F000753611d13s3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:d',
                        '/dev/dsk/c3t5742B0F000753611d13s4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:e',
                        '/dev/dsk/c3t5742B0F000753611d13s5': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:f',
                        '/dev/dsk/c3t5742B0F000753611d13s6': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:g',
                        '/dev/dsk/c3t5742B0F000753611d13s7': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:h',
                        '/dev/dsk/c3t5742B0F000753611d13s8': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:i',
                        '/dev/dsk/c3t5742B0F000753611d13s9': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d:j',
                        '/dev/dsk/c3t5742B0F000753611d14p0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:q',
                        '/dev/dsk/c3t5742B0F000753611d14p1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:r',
                        '/dev/dsk/c3t5742B0F000753611d14p2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:s',
                        '/dev/dsk/c3t5742B0F000753611d14p3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:t',
                        '/dev/dsk/c3t5742B0F000753611d14p4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:u',
                        '/dev/dsk/c3t5742B0F000753611d14s0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:a',
                        '/dev/dsk/c3t5742B0F000753611d14s1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:b',
                        '/dev/dsk/c3t5742B0F000753611d14s10': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:k',
                        '/dev/dsk/c3t5742B0F000753611d14s11': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:l',
                        '/dev/dsk/c3t5742B0F000753611d14s12': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:m',
                        '/dev/dsk/c3t5742B0F000753611d14s13': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:n',
                        '/dev/dsk/c3t5742B0F000753611d14s14': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:o',
                        '/dev/dsk/c3t5742B0F000753611d14s15': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:p',
                        '/dev/dsk/c3t5742B0F000753611d14s2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:c',
                        '/dev/dsk/c3t5742B0F000753611d14s3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:d',
                        '/dev/dsk/c3t5742B0F000753611d14s4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:e',
                        '/dev/dsk/c3t5742B0F000753611d14s5': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:f',
                        '/dev/dsk/c3t5742B0F000753611d14s6': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:g',
                        '/dev/dsk/c3t5742B0F000753611d14s7': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:h',
                        '/dev/dsk/c3t5742B0F000753611d14s8': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:i',
                        '/dev/dsk/c3t5742B0F000753611d14s9': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e:j',
                        '/dev/dsk/c3t5742B0F000753611d15p0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:q',
                        '/dev/dsk/c3t5742B0F000753611d15p1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:r',
                        '/dev/dsk/c3t5742B0F000753611d15p2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:s',
                        '/dev/dsk/c3t5742B0F000753611d15p3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:t',
                        '/dev/dsk/c3t5742B0F000753611d15p4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:u',
                        '/dev/dsk/c3t5742B0F000753611d15s0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:a',
                        '/dev/dsk/c3t5742B0F000753611d15s1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:b',
                        '/dev/dsk/c3t5742B0F000753611d15s10': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:k',
                        '/dev/dsk/c3t5742B0F000753611d15s11': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:l',
                        '/dev/dsk/c3t5742B0F000753611d15s12': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:m',
                        '/dev/dsk/c3t5742B0F000753611d15s13': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:n',
                        '/dev/dsk/c3t5742B0F000753611d15s14': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:o',
                        '/dev/dsk/c3t5742B0F000753611d15s15': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:p',
                        '/dev/dsk/c3t5742B0F000753611d15s2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:c',
                        '/dev/dsk/c3t5742B0F000753611d15s3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:d',
                        '/dev/dsk/c3t5742B0F000753611d15s4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:e',
                        '/dev/dsk/c3t5742B0F000753611d15s5': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:f',
                        '/dev/dsk/c3t5742B0F000753611d15s6': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:g',
                        '/dev/dsk/c3t5742B0F000753611d15s7': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:h',
                        '/dev/dsk/c3t5742B0F000753611d15s8': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:i',
                        '/dev/dsk/c3t5742B0F000753611d15s9': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f:j',
                        '/dev/dsk/c3t5742B0F000753611d16p0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:q',
                        '/dev/dsk/c3t5742B0F000753611d16p1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:r',
                        '/dev/dsk/c3t5742B0F000753611d16p2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:s',
                        '/dev/dsk/c3t5742B0F000753611d16p3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:t',
                        '/dev/dsk/c3t5742B0F000753611d16p4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:u',
                        '/dev/dsk/c3t5742B0F000753611d16s0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:a',
                        '/dev/dsk/c3t5742B0F000753611d16s1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:b',
                        '/dev/dsk/c3t5742B0F000753611d16s10': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:k',
                        '/dev/dsk/c3t5742B0F000753611d16s11': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:l',
                        '/dev/dsk/c3t5742B0F000753611d16s12': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:m',
                        '/dev/dsk/c3t5742B0F000753611d16s13': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:n',
                        '/dev/dsk/c3t5742B0F000753611d16s14': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:o',
                        '/dev/dsk/c3t5742B0F000753611d16s15': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:p',
                        '/dev/dsk/c3t5742B0F000753611d16s2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:c',
                        '/dev/dsk/c3t5742B0F000753611d16s3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:d',
                        '/dev/dsk/c3t5742B0F000753611d16s4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:e',
                        '/dev/dsk/c3t5742B0F000753611d16s5': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:f',
                        '/dev/dsk/c3t5742B0F000753611d16s6': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:g',
                        '/dev/dsk/c3t5742B0F000753611d16s7': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:h',
                        '/dev/dsk/c3t5742B0F000753611d16s8': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:i',
                        '/dev/dsk/c3t5742B0F000753611d16s9': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10:j',
                        '/dev/dsk/c3t5742B0F000753611d17p0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:q',
                        '/dev/dsk/c3t5742B0F000753611d17p1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:r',
                        '/dev/dsk/c3t5742B0F000753611d17p2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:s',
                        '/dev/dsk/c3t5742B0F000753611d17p3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:t',
                        '/dev/dsk/c3t5742B0F000753611d17p4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:u',
                        '/dev/dsk/c3t5742B0F000753611d17s0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:a',
                        '/dev/dsk/c3t5742B0F000753611d17s1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:b',
                        '/dev/dsk/c3t5742B0F000753611d17s10': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:k',
                        '/dev/dsk/c3t5742B0F000753611d17s11': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:l',
                        '/dev/dsk/c3t5742B0F000753611d17s12': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:m',
                        '/dev/dsk/c3t5742B0F000753611d17s13': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:n',
                        '/dev/dsk/c3t5742B0F000753611d17s14': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:o',
                        '/dev/dsk/c3t5742B0F000753611d17s15': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:p',
                        '/dev/dsk/c3t5742B0F000753611d17s2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:c',
                        '/dev/dsk/c3t5742B0F000753611d17s3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:d',
                        '/dev/dsk/c3t5742B0F000753611d17s4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:e',
                        '/dev/dsk/c3t5742B0F000753611d17s5': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:f',
                        '/dev/dsk/c3t5742B0F000753611d17s6': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:g',
                        '/dev/dsk/c3t5742B0F000753611d17s7': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:h',
                        '/dev/dsk/c3t5742B0F000753611d17s8': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:i',
                        '/dev/dsk/c3t5742B0F000753611d17s9': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11:j',
                        '/dev/dsk/c3t5742B0F000753611d18p0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:q',
                        '/dev/dsk/c3t5742B0F000753611d18p1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:r',
                        '/dev/dsk/c3t5742B0F000753611d18p2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:s',
                        '/dev/dsk/c3t5742B0F000753611d18p3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:t',
                        '/dev/dsk/c3t5742B0F000753611d18p4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:u',
                        '/dev/dsk/c3t5742B0F000753611d18s0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:a',
                        '/dev/dsk/c3t5742B0F000753611d18s1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:b',
                        '/dev/dsk/c3t5742B0F000753611d18s10': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:k',
                        '/dev/dsk/c3t5742B0F000753611d18s11': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:l',
                        '/dev/dsk/c3t5742B0F000753611d18s12': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:m',
                        '/dev/dsk/c3t5742B0F000753611d18s13': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:n',
                        '/dev/dsk/c3t5742B0F000753611d18s14': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:o',
                        '/dev/dsk/c3t5742B0F000753611d18s15': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:p',
                        '/dev/dsk/c3t5742B0F000753611d18s2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:c',
                        '/dev/dsk/c3t5742B0F000753611d18s3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:d',
                        '/dev/dsk/c3t5742B0F000753611d18s4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:e',
                        '/dev/dsk/c3t5742B0F000753611d18s5': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:f',
                        '/dev/dsk/c3t5742B0F000753611d18s6': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:g',
                        '/dev/dsk/c3t5742B0F000753611d18s7': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:h',
                        '/dev/dsk/c3t5742B0F000753611d18s8': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:i',
                        '/dev/dsk/c3t5742B0F000753611d18s9': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12:j',
                        '/dev/dsk/c3t5742B0F000753611d19p0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:q',
                        '/dev/dsk/c3t5742B0F000753611d19p1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:r',
                        '/dev/dsk/c3t5742B0F000753611d19p2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:s',
                        '/dev/dsk/c3t5742B0F000753611d19p3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:t',
                        '/dev/dsk/c3t5742B0F000753611d19p4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:u',
                        '/dev/dsk/c3t5742B0F000753611d19s0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:a',
                        '/dev/dsk/c3t5742B0F000753611d19s1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:b',
                        '/dev/dsk/c3t5742B0F000753611d19s10': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:k',
                        '/dev/dsk/c3t5742B0F000753611d19s11': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:l',
                        '/dev/dsk/c3t5742B0F000753611d19s12': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:m',
                        '/dev/dsk/c3t5742B0F000753611d19s13': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:n',
                        '/dev/dsk/c3t5742B0F000753611d19s14': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:o',
                        '/dev/dsk/c3t5742B0F000753611d19s15': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:p',
                        '/dev/dsk/c3t5742B0F000753611d19s2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:c',
                        '/dev/dsk/c3t5742B0F000753611d19s3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:d',
                        '/dev/dsk/c3t5742B0F000753611d19s4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:e',
                        '/dev/dsk/c3t5742B0F000753611d19s5': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:f',
                        '/dev/dsk/c3t5742B0F000753611d19s6': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:g',
                        '/dev/dsk/c3t5742B0F000753611d19s7': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:h',
                        '/dev/dsk/c3t5742B0F000753611d19s8': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:i',
                        '/dev/dsk/c3t5742B0F000753611d19s9': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13:j',
                        '/dev/dsk/c3t5742B0F000753611d1p0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:q',
                        '/dev/dsk/c3t5742B0F000753611d1p1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:r',
                        '/dev/dsk/c3t5742B0F000753611d1p2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:s',
                        '/dev/dsk/c3t5742B0F000753611d1p3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:t',
                        '/dev/dsk/c3t5742B0F000753611d1p4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:u',
                        '/dev/dsk/c3t5742B0F000753611d1s0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:a',
                        '/dev/dsk/c3t5742B0F000753611d1s1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:b',
                        '/dev/dsk/c3t5742B0F000753611d1s10': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:k',
                        '/dev/dsk/c3t5742B0F000753611d1s11': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:l',
                        '/dev/dsk/c3t5742B0F000753611d1s12': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:m',
                        '/dev/dsk/c3t5742B0F000753611d1s13': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:n',
                        '/dev/dsk/c3t5742B0F000753611d1s14': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:o',
                        '/dev/dsk/c3t5742B0F000753611d1s15': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:p',
                        '/dev/dsk/c3t5742B0F000753611d1s2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:c',
                        '/dev/dsk/c3t5742B0F000753611d1s3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:d',
                        '/dev/dsk/c3t5742B0F000753611d1s4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:e',
                        '/dev/dsk/c3t5742B0F000753611d1s5': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:f',
                        '/dev/dsk/c3t5742B0F000753611d1s6': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:g',
                        '/dev/dsk/c3t5742B0F000753611d1s7': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:h',
                        '/dev/dsk/c3t5742B0F000753611d1s8': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:i',
                        '/dev/dsk/c3t5742B0F000753611d1s9': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1:j',
                        '/dev/dsk/c3t5742B0F000753611d20p0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:q',
                        '/dev/dsk/c3t5742B0F000753611d20p1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:r',
                        '/dev/dsk/c3t5742B0F000753611d20p2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:s',
                        '/dev/dsk/c3t5742B0F000753611d20p3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:t',
                        '/dev/dsk/c3t5742B0F000753611d20p4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:u',
                        '/dev/dsk/c3t5742B0F000753611d20s0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:a',
                        '/dev/dsk/c3t5742B0F000753611d20s1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:b',
                        '/dev/dsk/c3t5742B0F000753611d20s10': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:k',
                        '/dev/dsk/c3t5742B0F000753611d20s11': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:l',
                        '/dev/dsk/c3t5742B0F000753611d20s12': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:m',
                        '/dev/dsk/c3t5742B0F000753611d20s13': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:n',
                        '/dev/dsk/c3t5742B0F000753611d20s14': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:o',
                        '/dev/dsk/c3t5742B0F000753611d20s15': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:p',
                        '/dev/dsk/c3t5742B0F000753611d20s2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:c',
                        '/dev/dsk/c3t5742B0F000753611d20s3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:d',
                        '/dev/dsk/c3t5742B0F000753611d20s4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:e',
                        '/dev/dsk/c3t5742B0F000753611d20s5': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:f',
                        '/dev/dsk/c3t5742B0F000753611d20s6': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:g',
                        '/dev/dsk/c3t5742B0F000753611d20s7': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:h',
                        '/dev/dsk/c3t5742B0F000753611d20s8': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:i',
                        '/dev/dsk/c3t5742B0F000753611d20s9': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14:j',
                        '/dev/dsk/c3t5742B0F000753611d2p0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:q',
                        '/dev/dsk/c3t5742B0F000753611d2p1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:r',
                        '/dev/dsk/c3t5742B0F000753611d2p2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:s',
                        '/dev/dsk/c3t5742B0F000753611d2p3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:t',
                        '/dev/dsk/c3t5742B0F000753611d2p4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:u',
                        '/dev/dsk/c3t5742B0F000753611d2s0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:a',
                        '/dev/dsk/c3t5742B0F000753611d2s1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:b',
                        '/dev/dsk/c3t5742B0F000753611d2s10': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:k',
                        '/dev/dsk/c3t5742B0F000753611d2s11': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:l',
                        '/dev/dsk/c3t5742B0F000753611d2s12': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:m',
                        '/dev/dsk/c3t5742B0F000753611d2s13': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:n',
                        '/dev/dsk/c3t5742B0F000753611d2s14': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:o',
                        '/dev/dsk/c3t5742B0F000753611d2s15': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:p',
                        '/dev/dsk/c3t5742B0F000753611d2s2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:c',
                        '/dev/dsk/c3t5742B0F000753611d2s3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:d',
                        '/dev/dsk/c3t5742B0F000753611d2s4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:e',
                        '/dev/dsk/c3t5742B0F000753611d2s5': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:f',
                        '/dev/dsk/c3t5742B0F000753611d2s6': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:g',
                        '/dev/dsk/c3t5742B0F000753611d2s7': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:h',
                        '/dev/dsk/c3t5742B0F000753611d2s8': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:i',
                        '/dev/dsk/c3t5742B0F000753611d2s9': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2:j',
                        '/dev/dsk/c3t5742B0F000753611d3p0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:q',
                        '/dev/dsk/c3t5742B0F000753611d3p1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:r',
                        '/dev/dsk/c3t5742B0F000753611d3p2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:s',
                        '/dev/dsk/c3t5742B0F000753611d3p3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:t',
                        '/dev/dsk/c3t5742B0F000753611d3p4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:u',
                        '/dev/dsk/c3t5742B0F000753611d3s0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:a',
                        '/dev/dsk/c3t5742B0F000753611d3s1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:b',
                        '/dev/dsk/c3t5742B0F000753611d3s10': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:k',
                        '/dev/dsk/c3t5742B0F000753611d3s11': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:l',
                        '/dev/dsk/c3t5742B0F000753611d3s12': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:m',
                        '/dev/dsk/c3t5742B0F000753611d3s13': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:n',
                        '/dev/dsk/c3t5742B0F000753611d3s14': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:o',
                        '/dev/dsk/c3t5742B0F000753611d3s15': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:p',
                        '/dev/dsk/c3t5742B0F000753611d3s2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:c',
                        '/dev/dsk/c3t5742B0F000753611d3s3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:d',
                        '/dev/dsk/c3t5742B0F000753611d3s4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:e',
                        '/dev/dsk/c3t5742B0F000753611d3s5': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:f',
                        '/dev/dsk/c3t5742B0F000753611d3s6': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:g',
                        '/dev/dsk/c3t5742B0F000753611d3s7': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:h',
                        '/dev/dsk/c3t5742B0F000753611d3s8': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:i',
                        '/dev/dsk/c3t5742B0F000753611d3s9': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3:j',
                        '/dev/dsk/c3t5742B0F000753611d4p0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:q',
                        '/dev/dsk/c3t5742B0F000753611d4p1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:r',
                        '/dev/dsk/c3t5742B0F000753611d4p2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:s',
                        '/dev/dsk/c3t5742B0F000753611d4p3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:t',
                        '/dev/dsk/c3t5742B0F000753611d4p4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:u',
                        '/dev/dsk/c3t5742B0F000753611d4s0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:a',
                        '/dev/dsk/c3t5742B0F000753611d4s1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:b',
                        '/dev/dsk/c3t5742B0F000753611d4s10': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:k',
                        '/dev/dsk/c3t5742B0F000753611d4s11': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:l',
                        '/dev/dsk/c3t5742B0F000753611d4s12': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:m',
                        '/dev/dsk/c3t5742B0F000753611d4s13': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:n',
                        '/dev/dsk/c3t5742B0F000753611d4s14': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:o',
                        '/dev/dsk/c3t5742B0F000753611d4s15': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:p',
                        '/dev/dsk/c3t5742B0F000753611d4s2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:c',
                        '/dev/dsk/c3t5742B0F000753611d4s3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:d',
                        '/dev/dsk/c3t5742B0F000753611d4s4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:e',
                        '/dev/dsk/c3t5742B0F000753611d4s5': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:f',
                        '/dev/dsk/c3t5742B0F000753611d4s6': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:g',
                        '/dev/dsk/c3t5742B0F000753611d4s7': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:h',
                        '/dev/dsk/c3t5742B0F000753611d4s8': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:i',
                        '/dev/dsk/c3t5742B0F000753611d4s9': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4:j',
                        '/dev/dsk/c3t5742B0F000753611d5p0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:q',
                        '/dev/dsk/c3t5742B0F000753611d5p1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:r',
                        '/dev/dsk/c3t5742B0F000753611d5p2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:s',
                        '/dev/dsk/c3t5742B0F000753611d5p3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:t',
                        '/dev/dsk/c3t5742B0F000753611d5p4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:u',
                        '/dev/dsk/c3t5742B0F000753611d5s0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:a',
                        '/dev/dsk/c3t5742B0F000753611d5s1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:b',
                        '/dev/dsk/c3t5742B0F000753611d5s10': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:k',
                        '/dev/dsk/c3t5742B0F000753611d5s11': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:l',
                        '/dev/dsk/c3t5742B0F000753611d5s12': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:m',
                        '/dev/dsk/c3t5742B0F000753611d5s13': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:n',
                        '/dev/dsk/c3t5742B0F000753611d5s14': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:o',
                        '/dev/dsk/c3t5742B0F000753611d5s15': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:p',
                        '/dev/dsk/c3t5742B0F000753611d5s2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:c',
                        '/dev/dsk/c3t5742B0F000753611d5s3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:d',
                        '/dev/dsk/c3t5742B0F000753611d5s4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:e',
                        '/dev/dsk/c3t5742B0F000753611d5s5': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:f',
                        '/dev/dsk/c3t5742B0F000753611d5s6': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:g',
                        '/dev/dsk/c3t5742B0F000753611d5s7': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:h',
                        '/dev/dsk/c3t5742B0F000753611d5s8': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:i',
                        '/dev/dsk/c3t5742B0F000753611d5s9': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5:j',
                        '/dev/dsk/c3t5742B0F000753611d6p0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:q',
                        '/dev/dsk/c3t5742B0F000753611d6p1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:r',
                        '/dev/dsk/c3t5742B0F000753611d6p2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:s',
                        '/dev/dsk/c3t5742B0F000753611d6p3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:t',
                        '/dev/dsk/c3t5742B0F000753611d6p4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:u',
                        '/dev/dsk/c3t5742B0F000753611d6s0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:a',
                        '/dev/dsk/c3t5742B0F000753611d6s1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:b',
                        '/dev/dsk/c3t5742B0F000753611d6s10': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:k',
                        '/dev/dsk/c3t5742B0F000753611d6s11': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:l',
                        '/dev/dsk/c3t5742B0F000753611d6s12': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:m',
                        '/dev/dsk/c3t5742B0F000753611d6s13': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:n',
                        '/dev/dsk/c3t5742B0F000753611d6s14': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:o',
                        '/dev/dsk/c3t5742B0F000753611d6s15': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:p',
                        '/dev/dsk/c3t5742B0F000753611d6s2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:c',
                        '/dev/dsk/c3t5742B0F000753611d6s3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:d',
                        '/dev/dsk/c3t5742B0F000753611d6s4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:e',
                        '/dev/dsk/c3t5742B0F000753611d6s5': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:f',
                        '/dev/dsk/c3t5742B0F000753611d6s6': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:g',
                        '/dev/dsk/c3t5742B0F000753611d6s7': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:h',
                        '/dev/dsk/c3t5742B0F000753611d6s8': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:i',
                        '/dev/dsk/c3t5742B0F000753611d6s9': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6:j',
                        '/dev/dsk/c3t5742B0F000753611d7p0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:q',
                        '/dev/dsk/c3t5742B0F000753611d7p1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:r',
                        '/dev/dsk/c3t5742B0F000753611d7p2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:s',
                        '/dev/dsk/c3t5742B0F000753611d7p3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:t',
                        '/dev/dsk/c3t5742B0F000753611d7p4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:u',
                        '/dev/dsk/c3t5742B0F000753611d7s0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:a',
                        '/dev/dsk/c3t5742B0F000753611d7s1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:b',
                        '/dev/dsk/c3t5742B0F000753611d7s10': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:k',
                        '/dev/dsk/c3t5742B0F000753611d7s11': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:l',
                        '/dev/dsk/c3t5742B0F000753611d7s12': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:m',
                        '/dev/dsk/c3t5742B0F000753611d7s13': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:n',
                        '/dev/dsk/c3t5742B0F000753611d7s14': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:o',
                        '/dev/dsk/c3t5742B0F000753611d7s15': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:p',
                        '/dev/dsk/c3t5742B0F000753611d7s2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:c',
                        '/dev/dsk/c3t5742B0F000753611d7s3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:d',
                        '/dev/dsk/c3t5742B0F000753611d7s4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:e',
                        '/dev/dsk/c3t5742B0F000753611d7s5': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:f',
                        '/dev/dsk/c3t5742B0F000753611d7s6': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:g',
                        '/dev/dsk/c3t5742B0F000753611d7s7': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:h',
                        '/dev/dsk/c3t5742B0F000753611d7s8': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:i',
                        '/dev/dsk/c3t5742B0F000753611d7s9': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7:j',
                        '/dev/dsk/c3t5742B0F000753611d8p0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:q',
                        '/dev/dsk/c3t5742B0F000753611d8p1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:r',
                        '/dev/dsk/c3t5742B0F000753611d8p2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:s',
                        '/dev/dsk/c3t5742B0F000753611d8p3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:t',
                        '/dev/dsk/c3t5742B0F000753611d8p4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:u',
                        '/dev/dsk/c3t5742B0F000753611d8s0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:a',
                        '/dev/dsk/c3t5742B0F000753611d8s1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:b',
                        '/dev/dsk/c3t5742B0F000753611d8s10': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:k',
                        '/dev/dsk/c3t5742B0F000753611d8s11': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:l',
                        '/dev/dsk/c3t5742B0F000753611d8s12': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:m',
                        '/dev/dsk/c3t5742B0F000753611d8s13': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:n',
                        '/dev/dsk/c3t5742B0F000753611d8s14': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:o',
                        '/dev/dsk/c3t5742B0F000753611d8s15': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:p',
                        '/dev/dsk/c3t5742B0F000753611d8s2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:c',
                        '/dev/dsk/c3t5742B0F000753611d8s3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:d',
                        '/dev/dsk/c3t5742B0F000753611d8s4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:e',
                        '/dev/dsk/c3t5742B0F000753611d8s5': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:f',
                        '/dev/dsk/c3t5742B0F000753611d8s6': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:g',
                        '/dev/dsk/c3t5742B0F000753611d8s7': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:h',
                        '/dev/dsk/c3t5742B0F000753611d8s8': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:i',
                        '/dev/dsk/c3t5742B0F000753611d8s9': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8:j',
                        '/dev/dsk/c3t5742B0F000753611d9p0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:q',
                        '/dev/dsk/c3t5742B0F000753611d9p1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:r',
                        '/dev/dsk/c3t5742B0F000753611d9p2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:s',
                        '/dev/dsk/c3t5742B0F000753611d9p3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:t',
                        '/dev/dsk/c3t5742B0F000753611d9p4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:u',
                        '/dev/dsk/c3t5742B0F000753611d9s0': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:a',
                        '/dev/dsk/c3t5742B0F000753611d9s1': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:b',
                        '/dev/dsk/c3t5742B0F000753611d9s10': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:k',
                        '/dev/dsk/c3t5742B0F000753611d9s11': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:l',
                        '/dev/dsk/c3t5742B0F000753611d9s12': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:m',
                        '/dev/dsk/c3t5742B0F000753611d9s13': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:n',
                        '/dev/dsk/c3t5742B0F000753611d9s14': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:o',
                        '/dev/dsk/c3t5742B0F000753611d9s15': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:p',
                        '/dev/dsk/c3t5742B0F000753611d9s2': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:c',
                        '/dev/dsk/c3t5742B0F000753611d9s3': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:d',
                        '/dev/dsk/c3t5742B0F000753611d9s4': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:e',
                        '/dev/dsk/c3t5742B0F000753611d9s5': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:f',
                        '/dev/dsk/c3t5742B0F000753611d9s6': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:g',
                        '/dev/dsk/c3t5742B0F000753611d9s7': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:h',
                        '/dev/dsk/c3t5742B0F000753611d9s8': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:i',
                        '/dev/dsk/c3t5742B0F000753611d9s9': '/devices/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9:j',
                        '/dev/dsk/c1t0d0p0': '/devices/pci@0,0/pci-ide@7,1/ide@1/sd@0,0:q',
                        '/dev/dsk/c1t0d0p1': '/devices/pci@0,0/pci-ide@7,1/ide@1/sd@0,0:r',
                        '/dev/dsk/c1t0d0p2': '/devices/pci@0,0/pci-ide@7,1/ide@1/sd@0,0:s',
                        '/dev/dsk/c1t0d0p3': '/devices/pci@0,0/pci-ide@7,1/ide@1/sd@0,0:t',
                        '/dev/dsk/c1t0d0p4': '/devices/pci@0,0/pci-ide@7,1/ide@1/sd@0,0:u',
                        '/dev/dsk/c1t0d0s0': '/devices/pci@0,0/pci-ide@7,1/ide@1/sd@0,0:a',
                        '/dev/dsk/c1t0d0s1': '/devices/pci@0,0/pci-ide@7,1/ide@1/sd@0,0:b',
                        '/dev/dsk/c1t0d0s10': '/devices/pci@0,0/pci-ide@7,1/ide@1/sd@0,0:k',
                        '/dev/dsk/c1t0d0s11': '/devices/pci@0,0/pci-ide@7,1/ide@1/sd@0,0:l',
                        '/dev/dsk/c1t0d0s12': '/devices/pci@0,0/pci-ide@7,1/ide@1/sd@0,0:m',
                        '/dev/dsk/c1t0d0s13': '/devices/pci@0,0/pci-ide@7,1/ide@1/sd@0,0:n',
                        '/dev/dsk/c1t0d0s14': '/devices/pci@0,0/pci-ide@7,1/ide@1/sd@0,0:o',
                        '/dev/dsk/c1t0d0s15': '/devices/pci@0,0/pci-ide@7,1/ide@1/sd@0,0:p',
                        '/dev/dsk/c1t0d0s2': '/devices/pci@0,0/pci-ide@7,1/ide@1/sd@0,0:c',
                        '/dev/dsk/c1t0d0s3': '/devices/pci@0,0/pci-ide@7,1/ide@1/sd@0,0:d',
                        '/dev/dsk/c1t0d0s4': '/devices/pci@0,0/pci-ide@7,1/ide@1/sd@0,0:e',
                        '/dev/dsk/c1t0d0s5': '/devices/pci@0,0/pci-ide@7,1/ide@1/sd@0,0:f',
                        '/dev/dsk/c1t0d0s6': '/devices/pci@0,0/pci-ide@7,1/ide@1/sd@0,0:g',
                        '/dev/dsk/c1t0d0s7': '/devices/pci@0,0/pci-ide@7,1/ide@1/sd@0,0:h',
                        '/dev/dsk/c1t0d0s8': '/devices/pci@0,0/pci-ide@7,1/ide@1/sd@0,0:i',
                        '/dev/dsk/c1t0d0s9': '/devices/pci@0,0/pci-ide@7,1/ide@1/sd@0,0:j',
                        '/dev/dsk/c2t0d0': '/devices/pci@0,0/pci15ad,1976@10/sd@0,0:wd',
                        '/dev/dsk/c2t0d0p0': '/devices/pci@0,0/pci15ad,1976@10/sd@0,0:q',
                        '/dev/dsk/c2t0d0p1': '/devices/pci@0,0/pci15ad,1976@10/sd@0,0:r',
                        '/dev/dsk/c2t0d0p2': '/devices/pci@0,0/pci15ad,1976@10/sd@0,0:s',
                        '/dev/dsk/c2t0d0p3': '/devices/pci@0,0/pci15ad,1976@10/sd@0,0:t',
                        '/dev/dsk/c2t0d0p4': '/devices/pci@0,0/pci15ad,1976@10/sd@0,0:u',
                        '/dev/dsk/c2t0d0s0': '/devices/pci@0,0/pci15ad,1976@10/sd@0,0:a',
                        '/dev/dsk/c2t0d0s1': '/devices/pci@0,0/pci15ad,1976@10/sd@0,0:b',
                        '/dev/dsk/c2t0d0s2': '/devices/pci@0,0/pci15ad,1976@10/sd@0,0:c',
                        '/dev/dsk/c2t0d0s3': '/devices/pci@0,0/pci15ad,1976@10/sd@0,0:d',
                        '/dev/dsk/c2t0d0s4': '/devices/pci@0,0/pci15ad,1976@10/sd@0,0:e',
                        '/dev/dsk/c2t0d0s5': '/devices/pci@0,0/pci15ad,1976@10/sd@0,0:f',
                        '/dev/dsk/c2t0d0s6': '/devices/pci@0,0/pci15ad,1976@10/sd@0,0:g'}

        listdir_map = {
            '/dev/dsk': ['c3t5742B0F000753611d10p0', 'c3t5742B0F000753611d10p1', 'c3t5742B0F000753611d10p2', 'c3t5742B0F000753611d10p3', 'c3t5742B0F000753611d10p4', 'c3t5742B0F000753611d10s0', 'c3t5742B0F000753611d10s1', 'c3t5742B0F000753611d10s10', 'c3t5742B0F000753611d10s11', 'c3t5742B0F000753611d10s12', 'c3t5742B0F000753611d10s13', 'c3t5742B0F000753611d10s14', 'c3t5742B0F000753611d10s15', 'c3t5742B0F000753611d10s2', 'c3t5742B0F000753611d10s3', 'c3t5742B0F000753611d10s4', 'c3t5742B0F000753611d10s5', 'c3t5742B0F000753611d10s6', 'c3t5742B0F000753611d10s7', 'c3t5742B0F000753611d10s8', 'c3t5742B0F000753611d10s9', 'c3t5742B0F000753611d11p0', 'c3t5742B0F000753611d11p1', 'c3t5742B0F000753611d11p2', 'c3t5742B0F000753611d11p3', 'c3t5742B0F000753611d11p4', 'c3t5742B0F000753611d11s0', 'c3t5742B0F000753611d11s1', 'c3t5742B0F000753611d11s10', 'c3t5742B0F000753611d11s11', 'c3t5742B0F000753611d11s12', 'c3t5742B0F000753611d11s13', 'c3t5742B0F000753611d11s14', 'c3t5742B0F000753611d11s15', 'c3t5742B0F000753611d11s2', 'c3t5742B0F000753611d11s3', 'c3t5742B0F000753611d11s4', 'c3t5742B0F000753611d11s5', 'c3t5742B0F000753611d11s6', 'c3t5742B0F000753611d11s7', 'c3t5742B0F000753611d11s8', 'c3t5742B0F000753611d11s9', 'c3t5742B0F000753611d12p0', 'c3t5742B0F000753611d12p1', 'c3t5742B0F000753611d12p2', 'c3t5742B0F000753611d12p3', 'c3t5742B0F000753611d12p4', 'c3t5742B0F000753611d12s0', 'c3t5742B0F000753611d12s1', 'c3t5742B0F000753611d12s10', 'c3t5742B0F000753611d12s11', 'c3t5742B0F000753611d12s12', 'c3t5742B0F000753611d12s13', 'c3t5742B0F000753611d12s14', 'c3t5742B0F000753611d12s15', 'c3t5742B0F000753611d12s2', 'c3t5742B0F000753611d12s3', 'c3t5742B0F000753611d12s4', 'c3t5742B0F000753611d12s5', 'c3t5742B0F000753611d12s6', 'c3t5742B0F000753611d12s7', 'c3t5742B0F000753611d12s8', 'c3t5742B0F000753611d12s9', 'c3t5742B0F000753611d13p0', 'c3t5742B0F000753611d13p1', 'c3t5742B0F000753611d13p2', 'c3t5742B0F000753611d13p3', 'c3t5742B0F000753611d13p4', 'c3t5742B0F000753611d13s0', 'c3t5742B0F000753611d13s1', 'c3t5742B0F000753611d13s10', 'c3t5742B0F000753611d13s11', 'c3t5742B0F000753611d13s12', 'c3t5742B0F000753611d13s13', 'c3t5742B0F000753611d13s14', 'c3t5742B0F000753611d13s15', 'c3t5742B0F000753611d13s2', 'c3t5742B0F000753611d13s3', 'c3t5742B0F000753611d13s4', 'c3t5742B0F000753611d13s5', 'c3t5742B0F000753611d13s6', 'c3t5742B0F000753611d13s7', 'c3t5742B0F000753611d13s8', 'c3t5742B0F000753611d13s9', 'c3t5742B0F000753611d14p0', 'c3t5742B0F000753611d14p1', 'c3t5742B0F000753611d14p2', 'c3t5742B0F000753611d14p3', 'c3t5742B0F000753611d14p4', 'c3t5742B0F000753611d14s0', 'c3t5742B0F000753611d14s1', 'c3t5742B0F000753611d14s10', 'c3t5742B0F000753611d14s11', 'c3t5742B0F000753611d14s12', 'c3t5742B0F000753611d14s13', 'c3t5742B0F000753611d14s14', 'c3t5742B0F000753611d14s15', 'c3t5742B0F000753611d14s2', 'c3t5742B0F000753611d14s3', 'c3t5742B0F000753611d14s4', 'c3t5742B0F000753611d14s5', 'c3t5742B0F000753611d14s6', 'c3t5742B0F000753611d14s7', 'c3t5742B0F000753611d14s8', 'c3t5742B0F000753611d14s9', 'c3t5742B0F000753611d15p0', 'c3t5742B0F000753611d15p1', 'c3t5742B0F000753611d15p2', 'c3t5742B0F000753611d15p3', 'c3t5742B0F000753611d15p4', 'c3t5742B0F000753611d15s0', 'c3t5742B0F000753611d15s1', 'c3t5742B0F000753611d15s10', 'c3t5742B0F000753611d15s11', 'c3t5742B0F000753611d15s12', 'c3t5742B0F000753611d15s13', 'c3t5742B0F000753611d15s14', 'c3t5742B0F000753611d15s15', 'c3t5742B0F000753611d15s2', 'c3t5742B0F000753611d15s3', 'c3t5742B0F000753611d15s4', 'c3t5742B0F000753611d15s5', 'c3t5742B0F000753611d15s6', 'c3t5742B0F000753611d15s7', 'c3t5742B0F000753611d15s8', 'c3t5742B0F000753611d15s9', 'c3t5742B0F000753611d16p0', 'c3t5742B0F000753611d16p1', 'c3t5742B0F000753611d16p2', 'c3t5742B0F000753611d16p3', 'c3t5742B0F000753611d16p4', 'c3t5742B0F000753611d16s0', 'c3t5742B0F000753611d16s1', 'c3t5742B0F000753611d16s10', 'c3t5742B0F000753611d16s11', 'c3t5742B0F000753611d16s12', 'c3t5742B0F000753611d16s13', 'c3t5742B0F000753611d16s14', 'c3t5742B0F000753611d16s15', 'c3t5742B0F000753611d16s2', 'c3t5742B0F000753611d16s3', 'c3t5742B0F000753611d16s4', 'c3t5742B0F000753611d16s5', 'c3t5742B0F000753611d16s6', 'c3t5742B0F000753611d16s7', 'c3t5742B0F000753611d16s8', 'c3t5742B0F000753611d16s9', 'c3t5742B0F000753611d17p0', 'c3t5742B0F000753611d17p1', 'c3t5742B0F000753611d17p2', 'c3t5742B0F000753611d17p3', 'c3t5742B0F000753611d17p4', 'c3t5742B0F000753611d17s0', 'c3t5742B0F000753611d17s1', 'c3t5742B0F000753611d17s10', 'c3t5742B0F000753611d17s11', 'c3t5742B0F000753611d17s12', 'c3t5742B0F000753611d17s13', 'c3t5742B0F000753611d17s14', 'c3t5742B0F000753611d17s15', 'c3t5742B0F000753611d17s2', 'c3t5742B0F000753611d17s3', 'c3t5742B0F000753611d17s4', 'c3t5742B0F000753611d17s5', 'c3t5742B0F000753611d17s6', 'c3t5742B0F000753611d17s7', 'c3t5742B0F000753611d17s8', 'c3t5742B0F000753611d17s9', 'c3t5742B0F000753611d18p0', 'c3t5742B0F000753611d18p1', 'c3t5742B0F000753611d18p2', 'c3t5742B0F000753611d18p3', 'c3t5742B0F000753611d18p4', 'c3t5742B0F000753611d18s0', 'c3t5742B0F000753611d18s1', 'c3t5742B0F000753611d18s10', 'c3t5742B0F000753611d18s11', 'c3t5742B0F000753611d18s12', 'c3t5742B0F000753611d18s13', 'c3t5742B0F000753611d18s14', 'c3t5742B0F000753611d18s15', 'c3t5742B0F000753611d18s2', 'c3t5742B0F000753611d18s3', 'c3t5742B0F000753611d18s4', 'c3t5742B0F000753611d18s5', 'c3t5742B0F000753611d18s6', 'c3t5742B0F000753611d18s7', 'c3t5742B0F000753611d18s8', 'c3t5742B0F000753611d18s9', 'c3t5742B0F000753611d19p0', 'c3t5742B0F000753611d19p1', 'c3t5742B0F000753611d19p2', 'c3t5742B0F000753611d19p3', 'c3t5742B0F000753611d19p4', 'c3t5742B0F000753611d19s0', 'c3t5742B0F000753611d19s1', 'c3t5742B0F000753611d19s10', 'c3t5742B0F000753611d19s11', 'c3t5742B0F000753611d19s12', 'c3t5742B0F000753611d19s13', 'c3t5742B0F000753611d19s14', 'c3t5742B0F000753611d19s15', 'c3t5742B0F000753611d19s2', 'c3t5742B0F000753611d19s3', 'c3t5742B0F000753611d19s4', 'c3t5742B0F000753611d19s5', 'c3t5742B0F000753611d19s6', 'c3t5742B0F000753611d19s7', 'c3t5742B0F000753611d19s8', 'c3t5742B0F000753611d19s9', 'c3t5742B0F000753611d1p0', 'c3t5742B0F000753611d1p1', 'c3t5742B0F000753611d1p2', 'c3t5742B0F000753611d1p3', 'c3t5742B0F000753611d1p4', 'c3t5742B0F000753611d1s0', 'c3t5742B0F000753611d1s1', 'c3t5742B0F000753611d1s10', 'c3t5742B0F000753611d1s11', 'c3t5742B0F000753611d1s12', 'c3t5742B0F000753611d1s13', 'c3t5742B0F000753611d1s14', 'c3t5742B0F000753611d1s15', 'c3t5742B0F000753611d1s2', 'c3t5742B0F000753611d1s3', 'c3t5742B0F000753611d1s4', 'c3t5742B0F000753611d1s5', 'c3t5742B0F000753611d1s6', 'c3t5742B0F000753611d1s7', 'c3t5742B0F000753611d1s8', 'c3t5742B0F000753611d1s9', 'c3t5742B0F000753611d20p0', 'c3t5742B0F000753611d20p1', 'c3t5742B0F000753611d20p2', 'c3t5742B0F000753611d20p3', 'c3t5742B0F000753611d20p4', 'c3t5742B0F000753611d20s0', 'c3t5742B0F000753611d20s1', 'c3t5742B0F000753611d20s10', 'c3t5742B0F000753611d20s11', 'c3t5742B0F000753611d20s12', 'c3t5742B0F000753611d20s13', 'c3t5742B0F000753611d20s14', 'c3t5742B0F000753611d20s15', 'c3t5742B0F000753611d20s2', 'c3t5742B0F000753611d20s3', 'c3t5742B0F000753611d20s4', 'c3t5742B0F000753611d20s5', 'c3t5742B0F000753611d20s6', 'c3t5742B0F000753611d20s7', 'c3t5742B0F000753611d20s8', 'c3t5742B0F000753611d20s9', 'c3t5742B0F000753611d2p0', 'c3t5742B0F000753611d2p1', 'c3t5742B0F000753611d2p2', 'c3t5742B0F000753611d2p3', 'c3t5742B0F000753611d2p4', 'c3t5742B0F000753611d2s0', 'c3t5742B0F000753611d2s1', 'c3t5742B0F000753611d2s10', 'c3t5742B0F000753611d2s11', 'c3t5742B0F000753611d2s12', 'c3t5742B0F000753611d2s13', 'c3t5742B0F000753611d2s14', 'c3t5742B0F000753611d2s15', 'c3t5742B0F000753611d2s2', 'c3t5742B0F000753611d2s3', 'c3t5742B0F000753611d2s4', 'c3t5742B0F000753611d2s5', 'c3t5742B0F000753611d2s6', 'c3t5742B0F000753611d2s7', 'c3t5742B0F000753611d2s8', 'c3t5742B0F000753611d2s9', 'c3t5742B0F000753611d3p0', 'c3t5742B0F000753611d3p1', 'c3t5742B0F000753611d3p2', 'c3t5742B0F000753611d3p3', 'c3t5742B0F000753611d3p4', 'c3t5742B0F000753611d3s0', 'c3t5742B0F000753611d3s1', 'c3t5742B0F000753611d3s10', 'c3t5742B0F000753611d3s11', 'c3t5742B0F000753611d3s12', 'c3t5742B0F000753611d3s13', 'c3t5742B0F000753611d3s14', 'c3t5742B0F000753611d3s15', 'c3t5742B0F000753611d3s2', 'c3t5742B0F000753611d3s3', 'c3t5742B0F000753611d3s4', 'c3t5742B0F000753611d3s5', 'c3t5742B0F000753611d3s6', 'c3t5742B0F000753611d3s7', 'c3t5742B0F000753611d3s8', 'c3t5742B0F000753611d3s9', 'c3t5742B0F000753611d4p0', 'c3t5742B0F000753611d4p1', 'c3t5742B0F000753611d4p2', 'c3t5742B0F000753611d4p3', 'c3t5742B0F000753611d4p4', 'c3t5742B0F000753611d4s0', 'c3t5742B0F000753611d4s1', 'c3t5742B0F000753611d4s10', 'c3t5742B0F000753611d4s11', 'c3t5742B0F000753611d4s12', 'c3t5742B0F000753611d4s13', 'c3t5742B0F000753611d4s14', 'c3t5742B0F000753611d4s15', 'c3t5742B0F000753611d4s2', 'c3t5742B0F000753611d4s3', 'c3t5742B0F000753611d4s4', 'c3t5742B0F000753611d4s5', 'c3t5742B0F000753611d4s6', 'c3t5742B0F000753611d4s7', 'c3t5742B0F000753611d4s8', 'c3t5742B0F000753611d4s9', 'c3t5742B0F000753611d5p0', 'c3t5742B0F000753611d5p1', 'c3t5742B0F000753611d5p2', 'c3t5742B0F000753611d5p3', 'c3t5742B0F000753611d5p4', 'c3t5742B0F000753611d5s0', 'c3t5742B0F000753611d5s1', 'c3t5742B0F000753611d5s10', 'c3t5742B0F000753611d5s11', 'c3t5742B0F000753611d5s12', 'c3t5742B0F000753611d5s13', 'c3t5742B0F000753611d5s14', 'c3t5742B0F000753611d5s15', 'c3t5742B0F000753611d5s2', 'c3t5742B0F000753611d5s3', 'c3t5742B0F000753611d5s4', 'c3t5742B0F000753611d5s5', 'c3t5742B0F000753611d5s6', 'c3t5742B0F000753611d5s7', 'c3t5742B0F000753611d5s8', 'c3t5742B0F000753611d5s9', 'c3t5742B0F000753611d6p0', 'c3t5742B0F000753611d6p1', 'c3t5742B0F000753611d6p2', 'c3t5742B0F000753611d6p3', 'c3t5742B0F000753611d6p4', 'c3t5742B0F000753611d6s0', 'c3t5742B0F000753611d6s1', 'c3t5742B0F000753611d6s10', 'c3t5742B0F000753611d6s11', 'c3t5742B0F000753611d6s12', 'c3t5742B0F000753611d6s13', 'c3t5742B0F000753611d6s14', 'c3t5742B0F000753611d6s15', 'c3t5742B0F000753611d6s2', 'c3t5742B0F000753611d6s3', 'c3t5742B0F000753611d6s4', 'c3t5742B0F000753611d6s5', 'c3t5742B0F000753611d6s6', 'c3t5742B0F000753611d6s7', 'c3t5742B0F000753611d6s8', 'c3t5742B0F000753611d6s9', 'c3t5742B0F000753611d7p0', 'c3t5742B0F000753611d7p1', 'c3t5742B0F000753611d7p2', 'c3t5742B0F000753611d7p3', 'c3t5742B0F000753611d7p4', 'c3t5742B0F000753611d7s0', 'c3t5742B0F000753611d7s1', 'c3t5742B0F000753611d7s10', 'c3t5742B0F000753611d7s11', 'c3t5742B0F000753611d7s12', 'c3t5742B0F000753611d7s13', 'c3t5742B0F000753611d7s14', 'c3t5742B0F000753611d7s15', 'c3t5742B0F000753611d7s2', 'c3t5742B0F000753611d7s3', 'c3t5742B0F000753611d7s4', 'c3t5742B0F000753611d7s5', 'c3t5742B0F000753611d7s6', 'c3t5742B0F000753611d7s7', 'c3t5742B0F000753611d7s8', 'c3t5742B0F000753611d7s9', 'c3t5742B0F000753611d8p0', 'c3t5742B0F000753611d8p1', 'c3t5742B0F000753611d8p2', 'c3t5742B0F000753611d8p3', 'c3t5742B0F000753611d8p4', 'c3t5742B0F000753611d8s0', 'c3t5742B0F000753611d8s1', 'c3t5742B0F000753611d8s10', 'c3t5742B0F000753611d8s11', 'c3t5742B0F000753611d8s12', 'c3t5742B0F000753611d8s13', 'c3t5742B0F000753611d8s14', 'c3t5742B0F000753611d8s15', 'c3t5742B0F000753611d8s2', 'c3t5742B0F000753611d8s3', 'c3t5742B0F000753611d8s4', 'c3t5742B0F000753611d8s5', 'c3t5742B0F000753611d8s6', 'c3t5742B0F000753611d8s7', 'c3t5742B0F000753611d8s8', 'c3t5742B0F000753611d8s9', 'c3t5742B0F000753611d9p0', 'c3t5742B0F000753611d9p1', 'c3t5742B0F000753611d9p2', 'c3t5742B0F000753611d9p3', 'c3t5742B0F000753611d9p4', 'c3t5742B0F000753611d9s0', 'c3t5742B0F000753611d9s1', 'c3t5742B0F000753611d9s10', 'c3t5742B0F000753611d9s11', 'c3t5742B0F000753611d9s12', 'c3t5742B0F000753611d9s13', 'c3t5742B0F000753611d9s14', 'c3t5742B0F000753611d9s15', 'c3t5742B0F000753611d9s2', 'c3t5742B0F000753611d9s3', 'c3t5742B0F000753611d9s4', 'c3t5742B0F000753611d9s5', 'c3t5742B0F000753611d9s6', 'c3t5742B0F000753611d9s7', 'c3t5742B0F000753611d9s8', 'c3t5742B0F000753611d9s9',
                         'c1t0d0p0', 'c1t0d0p1', 'c1t0d0p2', 'c1t0d0p3', 'c1t0d0p4', 'c1t0d0s0', 'c1t0d0s1', 'c1t0d0s10', 'c1t0d0s11', 'c1t0d0s12', 'c1t0d0s13', 'c1t0d0s14', 'c1t0d0s15', 'c1t0d0s2', 'c1t0d0s3', 'c1t0d0s4', 'c1t0d0s5', 'c1t0d0s6', 'c1t0d0s7', 'c1t0d0s8', 'c1t0d0s9', 'c2t0d0', 'c2t0d0p0', 'c2t0d0p1', 'c2t0d0p2', 'c2t0d0p3', 'c2t0d0p4', 'c2t0d0s0', 'c2t0d0s1', 'c2t0d0s2', 'c2t0d0s3', 'c2t0d0s4', 'c2t0d0s5', 'c2t0d0s6']
        }

        file_map = {
            '/etc/path_to_inst': """
#
#       Caution! This file contains critical kernel state
#
"/fcoe" 0 "fcoe"
"/iscsi" 0 "iscsi"
"/options" 0 "options"
"/pseudo" 0 "pseudo"
"/scsi_vhci" 0 "scsi_vhci"
"/scsi_vhci/disk@g6742b0f000007536000000000000217d" 2 "sd"
"/scsi_vhci/disk@g6742b0f00000753600000000000028d5" 3 "sd"
"/scsi_vhci/disk@g6742b0f00000753600000000000028ef" 4 "sd"
"/scsi_vhci/disk@g6742b0f00000753600000000000028ee" 5 "sd"
"/scsi_vhci/disk@g6742b0f00000753600000000000028ed" 6 "sd"
"/scsi_vhci/disk@g6742b0f00000753600000000000028ec" 7 "sd"
"/scsi_vhci/disk@g6742b0f00000753600000000000028eb" 8 "sd"
"/scsi_vhci/disk@g6742b0f00000753600000000000028ea" 9 "sd"
"/scsi_vhci/disk@g6742b0f00000753600000000000028e9" 10 "sd"
"/scsi_vhci/disk@g6742b0f00000753600000000000028e8" 11 "sd"
"/scsi_vhci/disk@g6742b0f00000753600000000000028e7" 12 "sd"
"/scsi_vhci/disk@g6742b0f00000753600000000000028e6" 13 "sd"
"/scsi_vhci/disk@g6742b0f00000753600000000000028e5" 14 "sd"
"/scsi_vhci/disk@g6742b0f00000753600000000000028e4" 15 "sd"
"/scsi_vhci/disk@g6742b0f00000753600000000000028e3" 16 "sd"
"/scsi_vhci/disk@g6742b0f00000753600000000000028e2" 17 "sd"
"/scsi_vhci/disk@g6742b0f00000753600000000000028e0" 18 "sd"
"/scsi_vhci/disk@g6742b0f00000753600000000000028e1" 19 "sd"
"/scsi_vhci/disk@g6742b0f00000753600000000000028dd" 20 "sd"
"/scsi_vhci/disk@g6742b0f00000753600000000000028dc" 21 "sd"
"/scsi_vhci/disk@g6742b0f00000753600000000000028df" 22 "sd"
"/scsi_vhci/disk@g6742b0f00000753600000000000028de" 23 "sd"
"/vga_arbiter" 0 "vga_arbiter"
"/xsvc@0,0" 0 "xsvc"
"/pci@0,0" 0 "npe"
"/pci@0,0/isa@7" 0 "isa"
"/pci@0,0/isa@7/pit_beep" 0 "pit_beep"
"/pci@0,0/isa@7/i8042@1,60" 0 "i8042"
"/pci@0,0/isa@7/i8042@1,60/keyboard@0" 0 "kb8042"
"/pci@0,0/isa@7/i8042@1,60/mouse@1" 0 "mouse8042"
"/pci@0,0/isa@7/lp@1,378" 0 "ecpp"
"/pci@0,0/isa@7/asy@1,3f8" 0 "asy"
"/pci@0,0/isa@7/asy@1,2f8" 1 "asy"
"/pci@0,0/pci15ad,1976@10" 0 "mpt"
"/pci@0,0/pci15ad,1976@10/sd@0,0" 0 "sd"
"/pci@0,0/pci8086,7191@1" 0 "pci_pci"
"/pci@0,0/display@f" 0 "vgatext"
"/pci@0,0/pci15ad,7a0@15" 0 "pcieb"
"/pci@0,0/pci15ad,7a0@15/pci10df,f121@0" 0 "emlxs"
"/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0" 0 "fp"
"/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,14" 24 "sd"
"/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,13" 25 "sd"
"/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,12" 26 "sd"
"/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,11" 27 "sd"
"/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,10" 28 "sd"
"/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,f" 29 "sd"
"/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,e" 30 "sd"
"/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,d" 31 "sd"
"/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,c" 32 "sd"
"/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,b" 33 "sd"
"/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,a" 34 "sd"
"/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,9" 35 "sd"
"/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,8" 36 "sd"
"/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,7" 37 "sd"
"/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,6" 38 "sd"
"/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,5" 39 "sd"
"/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,4" 40 "sd"
"/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,3" 41 "sd"
"/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,2" 42 "sd"
"/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/disk@w5742b0f000753611,1" 43 "sd"
"/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@0,0/array-controller@w5742b0f000753611,0" 0 "sgen"
"/pci@0,0/pci15ad,7a0@15/pci10df,f121@0/fp@1,0" 1 "fp"
"/pci@0,0/pci15ad,7a0@15,1" 1 "pcieb"
"/pci@0,0/pci15ad,7a0@15,2" 2 "pcieb"
"/pci@0,0/pci15ad,7a0@15,3" 3 "pcieb"
"/pci@0,0/pci15ad,7a0@15,4" 4 "pcieb"
"/pci@0,0/pci15ad,7a0@15,5" 5 "pcieb"
"/pci@0,0/pci15ad,7a0@15,6" 6 "pcieb"
"/pci@0,0/pci15ad,7a0@15,7" 7 "pcieb"
"/pci@0,0/pci15ad,7a0@16" 8 "pcieb"
"/pci@0,0/pci15ad,7a0@16,1" 9 "pcieb"
"/pci@0,0/pci15ad,7a0@16,2" 10 "pcieb"
"/pci@0,0/pci15ad,7a0@16,3" 11 "pcieb"
"/pci@0,0/pci15ad,7a0@16,4" 12 "pcieb"
"/pci@0,0/pci15ad,7a0@16,5" 13 "pcieb"
"/pci@0,0/pci15ad,7a0@16,6" 14 "pcieb"
"/pci@0,0/pci15ad,7a0@16,7" 15 "pcieb"
"/pci@0,0/pci15ad,7a0@17" 16 "pcieb"
"/pci@0,0/pci15ad,7a0@17,1" 17 "pcieb"
"/pci@0,0/pci15ad,7a0@17,2" 18 "pcieb"
"/pci@0,0/pci15ad,7a0@17,3" 19 "pcieb"
"/pci@0,0/pci15ad,7a0@17,4" 20 "pcieb"
"/pci@0,0/pci15ad,7a0@17,5" 21 "pcieb"
"/pci@0,0/pci15ad,7a0@17,6" 22 "pcieb"
"/pci@0,0/pci15ad,7a0@17,7" 23 "pcieb"
"/pci@0,0/pci15ad,7a0@18" 24 "pcieb"
"/pci@0,0/pci15ad,7a0@18,1" 25 "pcieb"
"/pci@0,0/pci15ad,7a0@18,2" 26 "pcieb"
"/pci@0,0/pci15ad,7a0@18,3" 27 "pcieb"
"/pci@0,0/pci15ad,7a0@18,4" 28 "pcieb"
"/pci@0,0/pci15ad,7a0@18,5" 29 "pcieb"
"/pci@0,0/pci15ad,7a0@18,6" 30 "pcieb"
"/pci@0,0/pci15ad,7a0@18,7" 31 "pcieb"
"/pci@0,0/pci-ide@7,1" 0 "pci-ide"
"/pci@0,0/pci-ide@7,1/ide@0" 0 "ata"
"/pci@0,0/pci-ide@7,1/ide@1" 1 "ata"
"/pci@0,0/pci-ide@7,1/ide@1/sd@0,0" 1 "sd"
"/pci@0,0/pci15ad,790@11" 1 "pci_pci"
"/pci@0,0/pci15ad,790@11/pci15ad,750@0" 0 "e1000g"
"/fw" 0 "acpinex"
"/fw/sb@0" 1 "acpinex"
"/fw/sb@0/cpu@0" 0 "cpudrv"
"/fw/sb@0/L1M0@16" 2 "acpinex"
"/fw/sb@0/L1M0@16/L0M0@32" 3 "acpinex"
            """
        }

        def create_file_context_manager(*args, **kwargs):
            path = args[0]
            file_mock = Mock()
            file_mock.read = Mock(return_value=file_map[path])
            cm = Mock()
            cm.__enter__ = Mock(return_value=file_mock)
            cm.__exit__ = Mock()
            return cm

        def vid_side_effect(dev):
            if dev.get_block_access_path() == '/dev/rdsk/c2t0d0':
                return "crap", "crap"
            return "NFINIDAT", "InfiniBox"

        listdir_mock.side_effect = listdir_map.get
        readlink_mock.side_effect = readlink_map.get
        open_mock.side_effect = create_file_context_manager
        exists_mock.return_value = True
        get_vid_mock.side_effect = vid_side_effect

        from infi.storagemodel import get_storage_model
        scsi_model = get_storage_model().get_scsi()
        block_devices = scsi_model.get_all_scsi_block_devices()
        infinidat_block_devices = scsi_model.filter_vendor_specific_devices(block_devices, vid_pid)
        self.assertEquals(len(infinidat_block_devices), 20)
