from infi.storagemodel.errors import StorageModelError


class InvalidInfiniboxConnectivity(StorageModelError):
    pass


def get_system_serial_from_wwn(port_wwn):
    from infi.storagemodel.vendor.infinidat.infinibox.wwn import InfinidatWWN, InvalidWWN
    try:
        return InfinidatWWN(port_wwn).get_system_serial()
    except InvalidWWN:
        raise InvalidInfiniboxConnectivity("Invalid WWN {}".format(port_wwn))


def get_system_serial_from_iqn(iqn_str):
    from infi.dtypes.iqn import IQN, InvalidIQN
    try:
        last_iqn_field = IQN(iqn_str).get_extra_fields()[-1]
    except InvalidIQN:
        raise InvalidInfiniboxConnectivity("Invalid IQN {}".format(iqn_str))
    if last_iqn_field.startswith("infinibox-sn-"):
        try:
            return int(last_iqn_field.split("-")[-2])
        except ValueError:
            raise InvalidInfiniboxConnectivity("Invalid InfiniBox IQN {}".format(iqn_str))
    raise InvalidInfiniboxConnectivity("Could not get InfiniBox serial from IQN {}".format(iqn_str))


def get_system_serial_from_connectivity(connectivity):
    from infi.storagemodel.connectivity import FCConnectivity, ISCSIConnectivity
    if isinstance(connectivity, FCConnectivity):
        return get_system_serial_from_wwn(connectivity.get_target_wwn())
    if isinstance(connectivity, ISCSIConnectivity):
        return get_system_serial_from_iqn(connectivity.get_target_iqn())
    raise InvalidInfiniboxConnectivity("Could not get InfiniBox serial from connectivity {!r}".format(connectivity))


def get_system_serial_from_path(path):
    return get_system_serial_from_connectivity(path.get_connectivity())
