

def devlist():
    from infi.storagemodel import get_storage_model
    model = get_storage_model()

    scsi_block_devices = model.get_scsi().get_all_scsi_block_devices()
    mp_devices = model.get_native_multipath().get_all_multipath_devices()
    non_mp_devices = model.get_native_multipath().filter_non_multipath_scsi_block_devices(scsi_block_devices)

    infinibox_vid_pid = ("NFINIDAT", "InfiniBox")

    print "Multipath Devices"
    print "================="

    def print_multipath_device(device):
        print "\t".join([device.get_display_name(), str(device.get_size_in_bytes()), device.get_scsi_vendor_id(),
                         device.get_scsi_product_id(),
                         device.get_policy().get_display_name(), str(len(device.get_paths()))])
        for path in device.get_paths():
            print "\t" + "\t".join([path.get_path_id(), path.get_state(), str(path.get_hctl())])
            print "\t\t" + "\t".join([path.get_connectivity().get_initiator_wwn(),
                                      path.get_connectivity().get_target_wwn()])

    for device in model.get_native_multipath().filter_vendor_specific_devices(mp_devices, infinibox_vid_pid):
        print_multipath_device(device)
        mp_devices.pop(device)

    for device in mp_devices:
        print_multipath_device(device)

    def print_non_multipath_device(device):
        from infi.storagemodel.connectivity import FCConnectivity
        print "\t".join([device.get_display_name(), str(device.get_size_in_bytes()), device.get_scsi_vendor_id(),
                         device.get_scsi_product_id(),
                         str(device.get_hctl())])
        if isinstance(device.get_connectivity(), FCConnectivity):
            print "\t" + "\t".join([device.get_connectivity().get_initiator_wwn(),
                                    device.get_connectivity().get_target_wwn()])

    print "Non-Multipath Devices"
    print "====================="
    for device in model.get_scsi().filter_vendor_specific_devices(non_mp_devices, infinibox_vid_pid):
        print_non_multipath_device(device)
        non_mp_devices.pop(device)

    for device in non_mp_devices:
        print_non_multipath_device(device)
