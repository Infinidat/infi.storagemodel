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
