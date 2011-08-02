__import__("pkg_resources").declare_namespace(__name__)
from infi.exceptools import InfiException

__all__ = [ 'get_storage_model' ]

class StorageModelError(InfiException):
    pass

class StorageModelFindError(StorageModelError):
    pass

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
        print "\t".join([device.get_display_name(), str(device.get_size_in_bytes()), device.get_scsi_vendor_id(),
                         device.get_scsi_product_id(),
                         device.get_policy().get_name(), str(len(device.get_paths()))])
        for path in device.get_paths:
            print "\t" + "\t".join([path.get_path_id(), path.get_state(), str(path.get_hctl())])
            print "\t\t" + "\t".join([path.get_connectivity().get_initiator_wwn(),
                                      path.connectivity.get_target_wwn()])

    for device in model.native_multipath.filter_vendor_specific_devices(mp_devices, infinibox_vid_pid):
        print_multipath_device(device)
        mp_devices.pop(device)

    for device in mp_devices:
        print_multipath_device(device)

    def print_non_multipath_device(device):
        from .connectivity import FCConnectivity
        print "\t".join([device.get_display_name(), str(device.get_size_in_bytes()), device.get_scsi_vendor_id(),
                         device.get_scsi_product_id(),
                         str(device.get_hctl())])
        if isinstance(device.connectivity, FCConnectivity):
            print "\t" + "\t".join([device.connectivity().get_initiator_wwn(), device.connectivity().get_target_wwn()])

    print "Non-Multipath Devices"
    print "====================="
    for device in model.scsi.filter_vendor_specific_devices(non_mp_devices, infinibox_vid_pid):
        print_non_multipath_device(device)
        non_mp_devices.pop(device)

    for device in non_mp_devices:
        print_non_multipath_device(device)
