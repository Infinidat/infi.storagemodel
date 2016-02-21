from infi.storagemodel.predicates import FiberChannelMappingExists, FiberChannelMappingNotExists

from logging import getLogger
log = getLogger(__name__)


class InfinidatVolumeExists(object):
    """A predicate that checks if an Infinidat volume exists"""
    def __init__(self, system_serial, volume_id):
        self.system_serial = system_serial
        self.volume_id = volume_id

    def __call__(self):
        from ..shortcuts import get_infinidat_block_devices
        from infi.instruct.errors import InstructError
        from infi.asi.errors import AsiException
        devices_to_query = get_infinidat_block_devices()
        log.debug("Looking for Infinidat volume id {} from system id {}".format(self.volume_id, self.system_serial))
        for device in devices_to_query:
            device.get_scsi_test_unit_ready()
            try:
                if 0x83 not in device.get_scsi_inquiry_pages():
                    log.debug("No inquiry page 0x83 for device {!r}, returning False now as this should be fixed by rescan".format(device))
                    return False
                if device.get_vendor().get_naa() is None:
                    log.debug("NAA not found for device {!r}, returning False now as this should be fixed by rescan, next log message will be the EVPD '83h".format(device))
                    log.debug(repr(device.get_scsi_inquiry_pages()[0x83]))
                    return False
                volume_id = device.get_vendor().get_naa().get_volume_id()
                system_serial = device.get_vendor().get_naa().get_system_serial()
                log.debug("Found Infinidat volume id {} from system id {}".format(volume_id, system_serial))
            except (AsiException, InstructError):
                log.exception("failed to identify Infinidat volume, returning False now as this should be fixed by rescan")
                return False
        return any(self.volume_id == device.get_vendor().get_naa().get_volume_id() and
                   self.system_serial == device.get_vendor().get_naa().get_system_serial()
                   for device in devices_to_query)

    def __repr__(self):
        return "<{}(system_serial={!r}, volume_id={!r})>".format(self.__class__.__name__, self.system_serial, self.volume_id)


class InfinidatVolumeDoesNotExist(InfinidatVolumeExists):
    """A predicate that checks if an Infinidat volume does not exist"""
    def __call__(self):
        return not super(InfinidatVolumeDoesNotExist, self).__call__()


class FiberChannelMappingExistsUsingLinuxSG(FiberChannelMappingExists):
    def _get_chain_of_devices(self, model):
        from itertools import chain
        return chain(model.get_scsi().get_all_linux_scsi_generic_disk_devices(),
                     model.get_scsi().get_all_storage_controller_devices())

    def __repr__(self):
        return "<{}: {!r}>".format(self.__class__.__name__, self.connectivity)


class FiberChannelMappingNotExistsUsingLinuxSG(FiberChannelMappingExistsUsingLinuxSG):
    def __call__(self):
        return not super(FiberChannelMappingNotExistsUsingLinuxSG, self).__call__()


def get_predicate_for_checking_non_zero_host_id(system_serial, cluster_id=False):
    def all_storage_devices_on_logical_unit_0_of_specific_box_show_non_zero_host_id():
        from infi.storagemodel.vendor.infinidat.shortcuts import get_infinidat_block_devices_and_controllers__mapped_to_lun0
        from infi.storagemodel.errors import RescanIsNeeded
        devices = []

        try:
            devices.extend(get_infinidat_block_devices_and_controllers__mapped_to_lun0())
        except RescanIsNeeded:
            pass

        for device in devices:
            if cluster_id:
                if device.get_vendor().get_system_serial() == system_serial and device.get_vendor().get_cluster_id() == 0:
                    return False
            else:
                if device.get_vendor().get_system_serial() == system_serial and device.get_vendor().get_host_id() == 0:
                    return False
        return True

    return all_storage_devices_on_logical_unit_0_of_specific_box_show_non_zero_host_id
