
from logging import getLogger
from itertools import product

logger = getLogger(__name__)

__all__ = [
    'PredicateList',
    'DiskExists',
    'DiskNotExists',
    'MultipleFiberChannelMappingExist',
    'FiberChannelMappingExists',
    'MultipleFiberChannelMappingNotExist',
    'FiberChannelMappingNotExists',
    'WaitForNothing',
    'ScsiDevicesAreReady',
    'MultipathDevicesAreReady'
]

class PredicateList(object):
    """Returns True if all predicates in a given list return True"""
    def __init__(self, list_of_predicates):
        super(PredicateList, self).__init__()
        self._list_of_predicates = list_of_predicates

    def __call__(self):
        for predicate in self._list_of_predicates:
            result = predicate()
            logger.debug("Predicate {!r} returned {}".format(predicate, result))
            if not result:
                logger.debug("Returning False")
                return False
        logger.debug("Returning True")
        return True

    def __repr__(self):
        return "<PredicateList: {!r}>".format(self._list_of_predicates)


class DiskExists(object):
    """Returns True if a disk was discovered with the given scsi_serial_number"""

    def __init__(self, scsi_serial_number):
        super(DiskExists, self).__init__()
        self.scsi_serial_number = scsi_serial_number

    def __call__(self):
        from .. import get_storage_model
        model = get_storage_model()
        block_devices = model.get_scsi().get_all_scsi_block_devices()
        mp_devices = model.get_native_multipath().get_all_multipath_block_devices()
        non_mp_devices = list(model.get_native_multipath().filter_non_multipath_scsi_block_devices(block_devices))
        devices = mp_devices + non_mp_devices
        for device in devices:
            device.get_scsi_test_unit_ready()
        return any(device.get_scsi_serial_number() == self.scsi_serial_number
                   for device in devices)

    def __repr__(self):
        return "<{}: {}>".format(self.__class__.__name__, self.scsi_serial_number)


class DiskNotExists(DiskExists):
    """Returns True if a disk with the given scsi_serial_number has gone away"""

    def __call__(self):
        return not super(DiskNotExists, self).__call__()


def build_connectivity_object_from_wwn(initiator_wwn, target_wwn):
    """Returns a `infi.storagemodel.connectivity.FCConnectivity` instance for the given WWNs"""
    from infi.hbaapi import Port
    from ..connectivity import FCConnectivity
    local_port = Port()
    local_port.port_wwn = initiator_wwn
    remote_port = Port()
    remote_port.port_wwn = target_wwn
    return FCConnectivity(None, local_port, remote_port)


class MultipleFiberChannelMappingExist(object):
    """Returns True if a lun mapping was discovered"""
    def __init__(self, initiators, targets, lun_numbers):

        super(MultipleFiberChannelMappingExist, self).__init__()
        self._initiators = initiators
        self._targets = targets
        self._lun_numbers = lun_numbers
        self._expected_mappings = []
        self._assert_on_rpyc_netref()

    def _assert_on_rpyc_netref(self):
        suspects = [self._initiators, self._targets, self._lun_numbers]
        suspects.extend(self._initiators)
        suspects.extend(self._targets)
        suspects.extend(self._lun_numbers)
        for item in suspects:
            assert type(item).__name__.lower() != 'netref'

    def _build_product(self):
        self._expected_mappings = [(build_connectivity_object_from_wwn(initiator_wwn, target_wwn), lun_number)
                                   for initiator_wwn, target_wwn, lun_number in
                                   product(self._initiators, self._targets, self._lun_numbers)]

    def _is_fc_connectivity_a_match(self, device):
        logger.debug("Connectivity details: {!r}, Lun {}".format(device.get_connectivity(), device.get_hctl().get_lun()))
        for connectivity, lun_number in self._expected_mappings:
            if device.get_connectivity() == connectivity and device.get_hctl().get_lun() == lun_number:
                device.get_scsi_test_unit_ready()
                self._expected_mappings.remove((connectivity, lun_number))
                return True
        return False

    def _get_chain_of_devices(self, model):
        from itertools import chain
        return chain(model.get_scsi().get_all_scsi_block_devices(),
                     model.get_scsi().get_all_storage_controller_devices())

    def __call__(self):
        from .. import get_storage_model
        model = get_storage_model()
        self._build_product()
        logger.debug("Working on: {!r}".format(self))
        logger.debug("Looking for all scsi block devices")
        logger.debug("Expecting to find {} matches".format(len(self._expected_mappings)))
        for device in self._get_chain_of_devices(model):
            logger.debug("Found device: {!r}".format(device))
            if self._is_fc_connectivity_a_match(device):
                logger.debug("Connectivity matches, only {} more to go".format(self._expected_mappings))
        for device in model.get_native_multipath().get_all_multipath_block_devices():
            logger.debug("Found device: {!r}".format(device))
            for path in device.get_paths():
                if self._is_fc_connectivity_a_match(path):
                    logger.debug("Connectivity matches, only {} more to go".format(self._expected_mappings))
        if self._expected_mappings:
            logger.debug("Did not find all the mappings, {} missing".format(len(self._expected_mappings)))
            return False
        logger.debug("Found all expected mappings")
        return True

    def __repr__(self):
        text = "<{} (initiators={!r}, targets={!r}, luns={!r})>"
        return text.format(self.__class__.__name__, self._initiators, self._targets, self._lun_numbers)


class FiberChannelMappingExists(MultipleFiberChannelMappingExist):
    """Returns True if a lun mapping was discovered"""

    def __init__(self, initiator_wwn, target_wwn, lun_number):
        super(FiberChannelMappingExists, self).__init__([initiator_wwn], [target_wwn], [lun_number])


class MultipleFiberChannelMappingNotExist(MultipleFiberChannelMappingExist):
    """Returns True if a lun un-mapping was discovered"""

    def __call__(self):
        from .. import get_storage_model
        model = get_storage_model()
        self._build_product()
        initial_count = len(self._expected_mappings)
        logger.debug("Working on: {!r}".format(self))
        logger.debug("Looking for all scsi block devices")
        logger.debug("Expecting to not find {} matches".format(initial_count))
        for device in self._get_chain_of_devices(model):
            logger.debug("Found device: {!r}".format(device))
            if self._is_fc_connectivity_a_match(device):
                logger.debug("Found a connectivity match I wasn't supposed to find")
                return False
        for device in model.get_native_multipath().get_all_multipath_block_devices():
            logger.debug("Found device: {!r}".format(device))
            for path in device.get_paths():
                if self._is_fc_connectivity_a_match(path):
                    logger.debug("Found a connectivity match I wasn't supposed to find")
                    return False
        logger.debug("Did not find any of the expected mappings")
        return True


class FiberChannelMappingNotExists(MultipleFiberChannelMappingNotExist):
    """Returns True if a lun un-mapping was discovered"""

    def __init__(self, initiator_wwn, target_wwn, lun_number):
        super(FiberChannelMappingNotExists, self).__init__([initiator_wwn], [target_wwn], [lun_number])


class WaitForNothing(object):
    """Returns True immediately without waiting for anything"""

    def __call__(self):
        return True

    def __repr__(self):
        return "<WaitForNothing>"


class ScsiDevicesAreReady(object):
    """Returns True when all SCSI devices are ready"""

    def __call__(self):
        from infi.storagemodel import get_storage_model
        model = get_storage_model()
        scsi = model.get_scsi()
        [device.get_scsi_test_unit_ready() for device in scsi.get_all_storage_controller_devices()]
        [device.get_scsi_test_unit_ready() for device in scsi.get_all_scsi_block_devices()]
        return True

    def __repr__(self):
        return "<ScsiDevicesAreReady>"


class MultipathDevicesAreReady(object):
    """Returns True when all multipath devices are ready"""

    def __call__(self):
        from infi.storagemodel import get_storage_model
        model = get_storage_model()
        multipath = model.get_native_multipath()
        [device.get_scsi_test_unit_ready() for device in multipath.get_all_multipath_block_devices()]
        [device.get_scsi_test_unit_ready() for device in multipath.get_all_multipath_storage_controller_devices()]
        return True

    def __repr__(self):
        return "<MultipathDevicesAreReady>"
