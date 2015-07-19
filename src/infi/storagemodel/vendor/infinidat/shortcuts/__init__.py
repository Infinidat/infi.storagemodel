
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

def get_infinidat_non_multipathed_scsi_block_devices():
    all_scsi = get_infinidat_scsi_block_devices()
    model = infi.storagemodel.get_storage_model().get_native_multipath()
    return model.filter_non_multipath_scsi_block_devices(all_scsi)

def get_infinidat_veritas_multipath_block_devices():
    try:
        model = infi.storagemodel.get_storage_model().get_veritas_multipath()
    except NotImplementedError:
        return []
    return model.filter_vendor_specific_devices(model.get_all_multipath_block_devices(), vid_pid)

def get_infinidat_non_veritas_multipathed_scsi_block_devices():
    all_scsi = get_infinidat_scsi_block_devices()
    try:
        model = infi.storagemodel.get_storage_model().get_veritas_multipath()
    except NotImplementedError:
        return all_scsi
    return model.filter_non_multipath_scsi_block_devices(all_scsi)

def get_infinidat_non_multipathed_scsi_storage_controller_devices():
    all_scsi = get_infinidat_scsi_storage_controller_devices()
    model = infi.storagemodel.get_storage_model().get_native_multipath()
    return model.filter_non_multipath_scsi_storage_controller_devices(all_scsi)

def get_infinidat_block_devices():
    """returns a list on NFINIDAT devices

    the devices returned by this function are by priority:
    * if veritas multipath devices exist, return those
    * else if native multipath devices exist, return those
    * else return the single-path deivces
    """
    veritas_multipath_devices = get_infinidat_veritas_multipath_block_devices()
    native_multipath_devices = get_infinidat_native_multipath_block_devices()
    veritas_non_multipath_devices = get_infinidat_non_veritas_multipathed_scsi_block_devices()
    native_non_multipath_devices = get_infinidat_non_multipathed_scsi_block_devices()
    if veritas_multipath_devices:
        return list(set(veritas_multipath_devices + veritas_non_multipath_devices))
    if native_multipath_devices:
        return list(set(native_multipath_devices + native_non_multipath_devices))

    # if veritas is installed the left one is empty and if not, the right one is empty
    return list(set(veritas_non_multipath_devices + native_non_multipath_devices))

def get_infinidat_storage_controller_devices():
    return get_infinidat_native_multipath_storage_controller_devices() + get_infinidat_non_multipathed_scsi_storage_controller_devices()

def get_infinidat_scsi_devices():
    return get_infinidat_scsi_block_devices() + get_infinidat_scsi_storage_controller_devices()

def get_infinidat_block_devices_and_controllers():
    return get_infinidat_storage_controller_devices() + get_infinidat_block_devices()

def get_infinidat_block_devices_and_controllers__mapped_to_lun0():
    from infi.storagemodel.base.multipath import MultipathBlockDevice, MultipathStorageController
    from infi.storagemodel.base.scsi import SCSIDevice, SCSIStorageController
    devices = get_infinidat_block_devices_and_controllers()
    return [device for device in devices if
            (isinstance(device, (SCSIDevice, SCSIStorageController)) and device.get_hctl().get_lun() == 0) or \
            (isinstance(device, (MultipathStorageController, MultipathBlockDevice)) and
             any(path.get_hctl().get_lun() == 0 for path in device.get_paths()))]
