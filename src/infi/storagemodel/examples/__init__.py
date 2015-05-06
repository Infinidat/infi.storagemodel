from __future__ import print_function


def devlist():
    # pylint: disable=R912

    from infi.storagemodel import get_storage_model
    from infi.storagemodel.vendor.infinidat.infinibox import vid_pid as infinibox_vid_pid
    model = get_storage_model()

    scsi_block_devices = model.get_scsi().get_all_scsi_block_devices()
    mp_devices = model.get_native_multipath().get_all_multipath_block_devices()
    non_mp_devices = model.get_native_multipath().filter_non_multipath_scsi_block_devices(scsi_block_devices)

    def print_header(header):
        print("%s\n%s" % (header, '=' * len(header)))

    print_header("Multipath Devices")

    def print_infinidat_device(device):
        print("skipping")

    def print_multipath_device(device):
        from infi.storagemodel.base.multipath import FailoverOnly, WeightedPaths, RoundRobinWithSubset
        print("{name}\t{size}MB\t{vid}\t{pid}\t{policy}\t{path_count}".format(name=device.get_display_name(),
                    size=device.get_size_in_bytes() / 1024 / 1024,
                    vid=device.get_scsi_vendor_id(), pid=device.get_scsi_product_id(),
                    policy=device.get_policy().get_display_name(), path_count=len(device.get_paths())))
        for path in device.get_paths():
            print("\t\t{id}\t{state}\t{hctl!r}".format(id=path.get_display_name(), state=path.get_state(),
                                                       hctl=path.get_hctl())),
            if isinstance(device.get_policy(), FailoverOnly):
                print("\t" + ("Active" if path.get_path_id() == device.get_policy().active_path_id else "Standby"))
            elif isinstance(device.get_policy(), RoundRobinWithSubset):
                print("\t" + ("Active" if path.get_path_id() in device.get_policy().active_path_ids else "Standby"))
            elif isinstance(device.get_policy(), WeightedPaths):
                print("\t" + "Weight " + str(device.get_policy().weights[path.get_path_id()]))
            else:
                print('')
            print("\t\t\t{} <--> {}".format(path.get_connectivity().get_initiator_wwn(),
                                          path.get_connectivity().get_target_wwn()))

    for device in model.get_native_multipath().filter_vendor_specific_devices(mp_devices, infinibox_vid_pid):
        print_multipath_device(device)
        print_infinidat_device(device)
        mp_devices.remove(device)

    for device in mp_devices:
        print_multipath_device(device)

    def print_non_multipath_device(device):
        from infi.storagemodel.connectivity import FCConnectivity
        print("{name}\t{size}MB\t{vid}\t{pid}\t{hctl}".format(name=device.get_display_name(),
                    size=device.get_size_in_bytes() / 1024 / 1024,
                    vid=device.get_scsi_vendor_id(), pid=device.get_scsi_product_id(),
                    hctl=device.get_hctl()))
        if isinstance(device.get_connectivity(), FCConnectivity):
            print("\t{} <-->".format(device.get_connectivity().get_initiator_wwn(),
                                     device.get_connectivity().get_target_wwn()))

    print_header("Non-Multipath Devices")

    for device in model.get_scsi().filter_vendor_specific_devices(non_mp_devices, infinibox_vid_pid):
        print_non_multipath_device(device)
        print_infinidat_device(device)
        non_mp_devices.remove(device)

    for device in non_mp_devices:
        print_non_multipath_device(device)
