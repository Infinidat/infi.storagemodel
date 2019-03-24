from infi.storagemodel.predicates import FiberChannelMappingExists, FiberChannelMappingNotExists

from logging import getLogger
log = getLogger(__name__)


def compare_device_system_and_id(device, system_serial, volume_id):
    ''' checks if given device is from a specific volume from a specific system '''
    from infi.storagemodel.base.multipath import MultipathBlockDevice
    from infi.storagemodel.vendor.infinidat.infinibox.connectivity import get_system_serial_from_path
    vendor = device.get_vendor()
    log_msg = "checking if device {} from system serial {} and volume id {} is from system serial {} with volume id {}"
    log.debug(log_msg.format(device.get_display_name(), vendor.get_system_serial(), vendor.get_volume_id(), system_serial, volume_id))
    if vendor.get_replication_type() == 'ACTIVE_ACTIVE' and isinstance(device, MultipathBlockDevice):
        replication_mapping = vendor.get_replication_mapping()
        log.debug("device is A/A replicated. mapping={}".format(replication_mapping))
        if (system_serial in replication_mapping and
           replication_mapping[system_serial].id == volume_id):
            # device is replicated to system_serial with volume_id but may not be mapped to the host
            return any(get_system_serial_from_path(path) == system_serial
                       for path in device.get_paths())
    # if the device is single-path or not under A/A replication it's ok to check by SCSI inquiry
    # because we'll always inquire the same, single system
    elif (volume_id == vendor.get_volume_id() and
         system_serial == vendor.get_system_serial()):
        return True
    return False


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
                # As some vendors seem to be inconsistent with the designators passed within the pages, using
                # vendor-specifc pages seems more safe:
                if 0xc6 not in device.get_scsi_inquiry_pages():
                    log.debug("No vendor-specific page 0xc6 for device {!r}, returning False now as this should be fixed by rescan".format(device))
                    return False
            except (AsiException, InstructError):
                log.exception("failed to identify INFINIDAT volume, returning False now as this should be fixed by rescan")
                return False
        return any(compare_device_system_and_id(device, self.system_serial, self.volume_id)
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
