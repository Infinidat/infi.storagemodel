from infi.storagemodel.errors import StorageModelError


class InvalidInfiniboxConnectivity(StorageModelError):
    pass

class LocalConnectivityException(StorageModelError):
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
            parts = last_iqn_field.split("-")
            # Due to a bug in infinisim we sometimes need to take parts[3] instead of parts[2] - INFRADEV-13513
            return int(parts[2] if parts[2].isdigit() else parts[3])
        except ValueError:
            raise InvalidInfiniboxConnectivity("Invalid InfiniBox IQN {}".format(iqn_str))
    raise InvalidInfiniboxConnectivity("Could not get InfiniBox serial from IQN {}".format(iqn_str))


def get_system_serial_from_connectivity(connectivity):
    from infi.storagemodel.connectivity import FCConnectivity, ISCSIConnectivity, LocalConnectivity
    if isinstance(connectivity, FCConnectivity):
        return get_system_serial_from_wwn(connectivity.get_target_wwn())
    if isinstance(connectivity, ISCSIConnectivity):
        return get_system_serial_from_iqn(connectivity.get_target_iqn())
    if isinstance(connectivity, LocalConnectivity):
        raise LocalConnectivityException("Local connectivity detected for Infinidat storage device, HBAAPI might be missing")
    raise InvalidInfiniboxConnectivity("Could not get InfiniBox serial from connectivity {!r}".format(connectivity))


def get_system_serial_from_path(path):
    return get_system_serial_from_connectivity(path.get_connectivity())
