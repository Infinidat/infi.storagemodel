__import__("pkg_resources").declare_namespace(__name__)

__all__ = [ 'get_storage_model' ]

__storage_model = None

def get_storage_model():
    global __storage_model
    if __storage_model is None:
        # do platform-specific magic here.
        from platform import system
        plat = system().lower().replace('-', '')
        exec "from .%s import %sStorageModel as PlatformStorageModel" % (plat, plat.capitalize())
        __storage_model = PlatformStorageModel()
    return __storage_model

#-----------------------------------------------------------
def infinidat_devlist_example():
    model = get_storage_model()

    scsi_block_devices = model.scsi.get_all_scsi_block_devices()
    mp_devices = model.native_multipath.get_devices()
    non_mp_devices = model.native_multipath.filter_non_multipath_scsi_block_devices(scsi_block_devices)

    infinibox_vid_pid = ("NFINIDAT", "InfiniBox")
    for device in model.native_multipath.filter_vendor_specific_devices(mp_devices, infinibox_vid_pid):
        print "\t".join([device.display_name, device.device_path, device.vendor.volume_name])
        mp_devices.pop(device)

    for device in model.scsi.filter_vendor_specific_devices(non_mp_devices, infinibox_vid_pid):
        print "\t".join([device.display_name, device.device_path, device.size_in_bytes])
        non_mp_devices.pop(device)
