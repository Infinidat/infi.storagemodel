
from infi.pyutils.lazy import cached_method, clear_cache

from logging import getLogger
logger = getLogger(__name__)

class PredicateList(object):
    """:returns: True if all predicates in a given list return True"""
    def __init__(self, list_of_predicates):
        super(PredicateList, self).__init__()
        self._list_of_predicates = list_of_predicates

    def __call__(self):
        results = []
        for predicate in self._list_of_predicates:
            result = predicate()
            logger.debug("Predicate {!r} returned {}".format(predicate, result))
            results.append(result)
        logger.debug("Returning {}".format(all(results)))
        return all(results)

    def __repr__(self):
        return "<PredicateList: {!r}>".format(self._list_of_predicates)

class DiskExists(object):
    """:returns: True if a disk was discovered with scsi_serial_number"""

    def __init__(self, scsi_serial_number):
        super(DiskExists, self).__init__()
        self.scsi_serial_number = scsi_serial_number

    def __call__(self):
        from .. import get_storage_model
        model = get_storage_model()
        block_devices = model.get_scsi().get_all_scsi_block_devices()
        mp_devices = model.get_native_multipath().get_all_multipath_block_devices()
        non_mp_devices = model.get_native_multipath().filter_non_multipath_scsi_block_devices(block_devices)
        devices = mp_devices + non_mp_devices
        for device in devices:
            device.get_scsi_test_unit_ready()
        return any([device.get_scsi_serial_number() == self.scsi_serial_number \
                    for device in devices])

    def __repr__(self):
        return "<DiskExists: {}>".format(self.scsi_serial_number)

class DiskNotExists(DiskExists):
    """:returns: True if a disk with scsi_serial_number has gone away"""

    def __call__(self):
        return not super(DiskNotExists, self).__call__()

    def __repr__(self):
        return "<DiskNotExists: {}>".format(self.scsi_serial_number)

class FiberChannelMappingExists(object):
    """:returns: True if a lun mapping was discovered"""

    def __init__(self, initiator_wwn, target_wwn, lun_number):
        super(FiberChannelMappingExists, self).__init__()

        from infi.hbaapi import Port
        from ..connectivity import FCConnectivity

        self.lun_number = lun_number

        i_port = Port()
        i_port.port_wwn = initiator_wwn
        t_port = Port()
        t_port.port_wwn = target_wwn
        self.connectivity = FCConnectivity(None, i_port, t_port)

    def _is_fc_connectivity_a_match(self, device):
        logger.debug("Connectivity details: {!r}".format(device.get_connectivity()))
        if device.get_connectivity() == self.connectivity and device.get_hctl().get_lun() == self.lun_number:
            return True
        return False

    def _get_chain_of_devices(self, model):
        from itertools import chain
        return chain(model.get_scsi().get_all_scsi_block_devices(),
                     model.get_scsi().get_all_storage_controller_devices())

    def __call__(self):
        from .. import get_storage_model
        model = get_storage_model()
        logger.debug("Working on: {!r}".format(self))
        logger.debug("Looking for all scsi block devices")
        for device in self._get_chain_of_devices(model):
            device.get_scsi_test_unit_ready()
            logger.debug("Found device: {!r}".format(device))
            if self._is_fc_connectivity_a_match(device):
                logger.debug("Connectivity matches")
                return True
        for device in model.get_native_multipath().get_all_multipath_block_devices():
            logger.debug("Found device: {!r}".format(device))
            for path in device.get_paths():
                if self._is_fc_connectivity_a_match(path):
                    logger.debug("Connectivity matches")
                    return True
        logger.debug("Did not find the requested connection")
        return False

    def __repr__(self):
        return "<FiberChannelMappingExists: {!r}>".format(self.connectivity)

class FiberChannelMappingNotExists(FiberChannelMappingExists):
    """:returns: True if a lun un-mapping was discovered"""
    def __call__(self):
        return not super(FiberChannelMappingNotExists, self).__call__()

    def __repr__(self):
        return "<FiberChannelMappingNotExists: {!r}>".format(self.connectivity)

class WaitForNothing(object):
    def __call__(self):
        return True

    def __repr__(self):
        return "<WaitForNothing>"

class ScsiDevicesAreReady(object):
    def __call__(self):
        from infi.storagemodel import get_storage_model
        model = get_storage_model()
        scsi = model.get_scsi()
        [device.get_scsi_test_unit_ready() for device in scsi.get_all_storage_controller_devices()]
        [device.get_scsi_test_unit_ready() for device in scsi.get_all_scsi_block_devices()]
        return True

    def __repr__(self):
        return "<ScsiDevicesAreReady>"
