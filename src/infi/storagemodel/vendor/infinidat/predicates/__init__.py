
from logging import getLogger
log = getLogger(__name__)

class InfinidatVolumeExists(object):
    """A predicate that checks if an Infinidat volume exists"""
    def __init__(self, system_serial, volume_id):
        self.system_serial = system_serial
        self.volume_id = volume_id

    def __call__(self):
        from infi.storagemodel import get_storage_model
        from ..shortcuts import get_infinidat_block_devices
        devices_to_query = get_infinidat_block_devices()
        log.debug("Looking for Infinidat volume id {} from system id {}".format(self.volume_id, self.system_serial))
        for device in devices_to_query:
            device.get_scsi_test_unit_ready()
            volume_id = device.get_vendor().get_naa().get_volume_id()
            system_serial = device.get_vendor().get_naa().get_system_serial()
            log.debug("Found Infinidat volume id {} from system id {}".format(volume_id, system_serial))
        return any([self.volume_id == device.get_vendor().get_naa().get_volume_id() and
                    self.system_serial == device.get_vendor().get_naa().get_system_serial() \
                    for device in devices_to_query])

    def __repr__(self):
        return "<InfinidatVolumeExists(system_serial={!r}, volume_id={!r})>".format(self.system_serial,
                                                                                    self.volume_id)

class InfinidatVolumeDoesNotExist(InfinidatVolumeExists):
    """A predicate that checks if an Infinidat volume does not exist"""
    def __call__(self):
        return not super(InfinidatVolumeDoesNotExist, self).__call__()

    def __repr__(self):
        return "<InfinidatVolumeDoesNotExist(system_serial={!r}, volume_id={!r})>".format(self.system_serial,
                                                                                          self.volume_id)

from infi.storagemodel.predicates import FiberChannelMappingExists, FiberChannelMappingNotExists

class FiberChannelMappingExistsUsingLinuxSG(FiberChannelMappingExists):
    def _get_chain_of_devices(self, model):
        from itertools import chain
        return chain(model.get_scsi().get_all_linux_scsi_generic_disk_devices(),
                     model.get_scsi().get_all_storage_controller_devices())

    def __repr__(self):
        return "<FiberChannelMappingExistsUsingLinuxSG: {!r}>".format(self.connectivity)

class FiberChannelMappingNotExistsUsingLinuxSG(FiberChannelMappingExistsUsingLinuxSG):
    def __call__(self):
        return not super(FiberChannelMappingNotExistsUsingLinuxSG, self).__call__()

    def __repr__(self):
        return "<FiberChannelMappingNotExistsUsingLinuxSG: {!r}>".format(self.connectivity)
