
import infi.storagemodel
from ..infinibox import vid_pid

def get_infinidat_scsi_storage_controller_devices():
    model = infi.storagemodel.get_storage_model().get_scsi()
    return model.filter_vendor_specific_devices(model.get_all_storage_controller_devices(), vid_pid)

def get_infinidat_scsi_block_devices():
    model = infi.storagemodel.get_storage_model().get_scsi()
    return model.filter_vendor_specific_devices(model.get_all_scsi_block_devices(), vid_pid)

def get_infinidat_native_multipath_block_devices():
    model = infi.storagemodel.get_storage_model().get_native_multipath()
    return model.filter_vendor_specific_devices(model.get_all_multipath_block_devices(), vid_pid)

def get_infinidat_native_multipath_storage_controller_devices():
    model = infi.storagemodel.get_storage_model().get_native_multipath()
    return model.filter_vendor_specific_devices(model.get_all_multipath_storage_controller_devices(), vid_pid)

def get_infinidat_non_multiathed_scsi_block_devices():
    all_scsi = get_infinidat_scsi_block_devices()
    model = infi.storagemodel.get_storage_model().get_native_multipath()
    return model.filter_non_multipath_scsi_block_devices(all_scsi)

def get_infinidat_non_multiathed_scsi_storage_controller_devices():
    all_scsi = get_infinidat_scsi_storage_controller_devices()
    model = infi.storagemodel.get_storage_model().get_native_multipath()
    return model.filter_non_multipath_scsi_storage_controller_devices(all_scsi)

def get_infinidat_block_devices():
    return get_infinidat_native_multipath_block_devices() + get_infinidat_non_multiathed_scsi_block_devices()

def get_infinidat_storage_controller_devices():
    return get_infinidat_native_multipath_storage_controller_devices() + get_infinidat_non_multiathed_scsi_storage_controller_devices()

def get_infinidat_scsi_devices():
    return get_infinidat_scsi_block_devices() + get_infinidat_scsi_storage_controller_devices()

def get_infinidat_block_devices_and_controllers():
    return get_infinidat_block_devices() + get_infinidat_storage_controller_devices()
