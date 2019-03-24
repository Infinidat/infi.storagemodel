from infi.storagemodel.errors import StorageModelError

def get_system_serial_from_wwn(port_wwn):
    from infi.storagemodel.vendor.infinidat.infinibox.wwn import InfinidatWWN
    return InfinidatWWN(port_wwn).get_system_serial()


def get_system_serial_from_iqn(iqn_str):
    from infi.dtypes.iqn import IQN
    last_iqn_field = IQN(iqn_str).get_extra_fields()[-1]
    if last_iqn_field.startswith("infinibox-sn-"):
        return int(last_iqn_field.split("-")[-2])
    raise StorageModelError("Could not get InfiniBox serial from IQN {}".format(iqn_str))


def get_system_serial_from_connectivity(connectivity):
    from infi.storagemodel.connectivity import FCConnectivity, ISCSIConnectivity
    if isinstance(connectivity, FCConnectivity):
        return get_system_serial_from_wwn(connectivity.get_target_wwn())
    if isinstance(connectivity, ISCSIConnectivity):
        return get_system_serial_from_iqn(connectivity.get_target_iqn())
    raise StorageModelError("Could not get InfiniBox serial from connectivity {!r}".format(connectivity))


def get_system_serial_from_path(path):
    return get_system_serial_from_connectivity(path.get_connectivity())
