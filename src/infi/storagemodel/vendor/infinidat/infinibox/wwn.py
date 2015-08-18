from infi.dtypes.wwn import WWN, InvalidWWN
from . import NFINIDAT_IEEE

TARGET_PATTERN = r"^5" + hex(NFINIDAT_IEEE)[2:] + "0(?P<system_serial>[A-Fa-f0-9]{6})(?P<node_id>[A-Fa-f0-9])(?P<port_id>[A-Fa-f0-9])$"
SOFT_TARGET_PATTERN = r"^2(?P<soft_target_id>[A-Fa-f0-9]{3})" + hex(NFINIDAT_IEEE)[2:] + "(?P<system_serial>[A-Fa-f0-9]{6})$"

def extract_infinibox_data_from_wwn(wwn):
    from re import match
    for pattern in [TARGET_PATTERN, SOFT_TARGET_PATTERN]:
        result = match(pattern, repr(wwn))
        if result is None:
            continue
        return result.groupdict()
    raise InvalidInfinidatWWN(wwn)


class InvalidInfinidatWWN(InvalidWWN):
    pass


class InfinidatWWN(WWN):
    def __init__(self, address):
        super(InfinidatWWN, self).__init__(address)
        self._groupdict = extract_infinibox_data_from_wwn(self)

    def get_system_serial(self):
        return int(self._groupdict['system_serial'], 16)

    def get_node_id(self):
        """:raises KeyError: in case of soft target port"""
        return int(self._groupdict['node_id'])

    def get_port_id(self):
        """:raises KeyError: in case of soft target port"""
        return int(self._groupdict['port_id'])

    def get_soft_target_id(self):
        """:raises KeyError: in case of non-NPIV target port"""
        return int(self._groupdict['soft_target_id'])

    def is_soft_target(self):
        return 'soft_target_id' in self._groupdict