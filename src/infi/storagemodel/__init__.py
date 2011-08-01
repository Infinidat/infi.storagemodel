__import__("pkg_resources").declare_namespace(__name__)

__all__ = [ 'get_storage_model' ]

__storage_model = None

def get_storage_model():
    global __storage_model
    if __storage_model is None:
        # do platform-specific magic here.
        from platform import system
        plat = system().lower().replace('-', '')
        from .base import StorageModel as PlatformStorageModel # helps IDEs
        exec "from .%s import %sStorageModel as PlatformStorageModel" % (plat, plat.capitalize())
        __storage_model = PlatformStorageModel()
    return __storage_model

#-----------------------------------------------------------
def infinidat_devlist_example():
    model = get_storage_model()

    scsi_block_devices = model.scsi.get_all_scsi_block_devices()
    mp_devices = model.native_multipath.get_all_multipath_devices()
    non_mp_devices = model.native_multipath.filter_non_multipath_scsi_block_devices(scsi_block_devices)

    infinibox_vid_pid = ("NFINIDAT", "InfiniBox")

    print "Multipath Devices"
    print "================="

    def print_multipath_device(device):
        print "\t".join([device.display_name, str(device.size_in_bytes), device.scsi_vendor_id, device.scsi_product_id,
                         device.policy.name, str(len(device.paths))])
        for path in device.paths:
            print "\t" + "\t".join([path.path_id, path.state, str(path.hctl)])
            print "\t\t" + "\t".join([path.connectivity.initiator_wwn, path.connectivity.target_wwn])

    for device in model.native_multipath.filter_vendor_specific_devices(mp_devices, infinibox_vid_pid):
        print_multipath_device(device)
        mp_devices.pop(device)

    for device in mp_devices:
        print_multipath_device(device)

    def print_non_multipath_device(device):
        from .connectivity import FCConnectivity
        print "\t".join([device.display_name, str(device.size_in_bytes), device.scsi_vendor_id, device.scsi_product_id,
                         str(device.hctl)])
        if isinstance(device.connectivity, FCConnectivity):
            print "\t" + "\t".join([device.connectivity.initiator_wwn, device.connectivity.target_wwn])

    print "Non-Multipath Devices"
    print "====================="
    for device in model.scsi.filter_vendor_specific_devices(non_mp_devices, infinibox_vid_pid):
        print_non_multipath_device(device)
        non_mp_devices.pop(device)

    for device in non_mp_devices:
        print_non_multipath_device(device)
