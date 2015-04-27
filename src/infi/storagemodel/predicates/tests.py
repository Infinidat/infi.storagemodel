import unittest
import mock

from ..base import StorageModel, scsi, multipath
from .. import connectivity
from infi.dtypes.hctl import HCTL

# pylint: disable=W0312,W0212,W0710,R0904,W0223


class MultipathModelImpl(multipath.MultipathFrameworkModel):
    def __init__(self, *args, **kwargs):
        multipath.MultipathFrameworkModel.__init__(self, *args, **kwargs)
        self._devices = []

    def get_all_multipath_block_devices(self):
        return self._devices

    def filter_non_multipath_scsi_block_devices(self, scsi_devices):
        return scsi_devices


class SCSIMockImpl(scsi.SCSIModel):
    def __init__(self, *args, **kwargs):
        scsi.SCSIModel.__init__(self, *args, **kwargs)
        self._devices = []

    def get_all_scsi_block_devices(self):
        return self._devices

    def get_all_storage_controller_devices(self):
        return []


MultipathModel = MultipathModelImpl()
SCSIModel = SCSIMockImpl()


class MockModel(StorageModel):
    def _initiate_rescan(self, wait_for_completion=False, raise_error=False):
        pass

    def _create_native_multipath_model(self):
        return MultipathModel

    def _create_scsi_model(self):
        return SCSIModel


class Disk(object):
    def __init__(self, scsi_serial_number):
        self.scsi_serial_number = scsi_serial_number
        self.called = False
        self.connectivity = False
        self.hctl = None

    @property
    def test(self):
        if not self.called:
            self.called = True

    def get_hctl(self):
        return self.hctl

    def get_scsi_serial_number(self):
        return self.scsi_serial_number

    def get_connectivity(self):
        return self.connectivity

    def get_scsi_test_unit_ready(self):
        return None


class FCConectivityMock(connectivity.FCConnectivity):
    def __init__(self, i_wwn, t_wwn):
        from infi.hbaapi import Port
        i_port = Port()
        t_port = Port()
        i_port.port_wwn = i_wwn
        t_port.port_wwn = t_wwn
        super(FCConectivityMock, self).__init__(None, i_port, t_port)


class PredicateTestCase(unittest.TestCase):
    def true(self):
        return True

    def false(self):
        return False

    def test_getmemmbers(self):
        from inspect import getmembers
        disk = Disk('1')
        self.assertFalse(disk.called)
        getmembers(disk)
        self.assertTrue(disk.called)

    def test_rescan_with_mock_predicate__returns_true(self):
        model = MockModel()
        model.rescan_and_wait_for(self.true)

    def test_rescan_with_mock_predicate__raises_timeout(self):
        from ..errors import TimeoutError
        model = MockModel()
        self.assertRaises(TimeoutError, model.rescan_and_wait_for, *(self.false, 1))

    def test__predicate_list(self):
        from . import PredicateList
        self.assertTrue(PredicateList([self.true, self.true])())
        self.assertFalse(PredicateList([self.true, self.false])())
        self.assertFalse(PredicateList([self.false, self.true])())
        self.assertFalse(PredicateList([self.false, self.false])())

    @mock.patch("infi.storagemodel.get_storage_model")
    def test__disk_appeared(self, get_storage_model):
        from . import DiskExists
        get_storage_model.return_value = MockModel()
        self.assertFalse(DiskExists("12345678")())
        SCSIModel._devices = [Disk("12345678")]
        self.assertTrue(DiskExists("12345678")())
        SCSIModel._devices = []
        MultipathModel._devices = [Disk("12345678")]
        self.assertTrue(DiskExists("12345678")())
        MultipathModel._devices = []

    @mock.patch("infi.storagemodel.get_storage_model")
    def test__disk_gone(self, get_storage_model):
        from . import DiskNotExists
        get_storage_model.return_value = MockModel()
        self.assertTrue(DiskNotExists("12345678")())
        SCSIModel._devices = [Disk("12345678")]
        self.assertFalse(DiskNotExists("12345678")())
        SCSIModel._devices = []
        MultipathModel._devices = [Disk("12345678")]
        self.assertFalse(DiskNotExists("12345678")())
        MultipathModel._devices = []

    @mock.patch("infi.storagemodel.get_storage_model")
    def test__fc_mapping_appeared(self, get_storage_model):
        from . import FiberChannelMappingExists, MultipleFiberChannelMappingExist
        i_wwn = ":".join(["01"] * 8)
        t_wwn = ":".join(["02"] * 8)
        get_storage_model.return_value = MockModel()
        self.assertFalse(FiberChannelMappingExists(i_wwn, t_wwn, 1)())
        self.assertFalse(MultipleFiberChannelMappingExist([i_wwn], [t_wwn], [1])())
        SCSIModel._devices = [Disk("1")]
        SCSIModel._devices[0].connectivity = FCConectivityMock(i_wwn, t_wwn)
        SCSIModel._devices[0].hctl = HCTL(1, 0, 0, 1)
        self.assertTrue(FiberChannelMappingExists(i_wwn, t_wwn, 1)())
        self.assertTrue(MultipleFiberChannelMappingExist([i_wwn], [t_wwn], [1])())
        SCSIModel._devices = []

    @mock.patch("infi.storagemodel.get_storage_model")
    def test_fc_mapping_gone(self, get_storage_model):
        from . import FiberChannelMappingNotExists, MultipleFiberChannelMappingNotExist
        i_wwn = ":".join(["01"] * 8)
        t_wwn = ":".join(["02"] * 8)
        get_storage_model.return_value = MockModel()
        SCSIModel._devices = [Disk("1")]
        SCSIModel._devices[0].connectivity = FCConectivityMock(i_wwn, t_wwn)
        SCSIModel._devices[0].hctl = HCTL(1, 0, 0, 1)
        self.assertFalse(FiberChannelMappingNotExists(i_wwn, t_wwn, 1)())
        self.assertFalse(MultipleFiberChannelMappingNotExist([i_wwn], [t_wwn], [1, 2])())
        SCSIModel._devices = []
        self.assertTrue(FiberChannelMappingNotExists(i_wwn, t_wwn, 1)())
        self.assertTrue(MultipleFiberChannelMappingNotExist([i_wwn], [t_wwn], [1, 2]))

# TODO add rescan tests on real host with the predicates
