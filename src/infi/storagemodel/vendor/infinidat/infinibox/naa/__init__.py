import struct
from .....errors import StorageModelError
from .. import NFINIDAT_IEEE
from infi.asi.cdb.inquiry.vpd_pages import designators


class InfinidatNAA(object):
    def __init__(self, data):
        super(InfinidatNAA, self).__init__()
        if isinstance(data, (str, bytes)):
            data = self._string_to_designator(data)
        if not isinstance(data, designators.NAA_IEEE_Registered_Extended_Designator):
            raise StorageModelError("Invalid argument type {!r}".format(data))
        self._data = data

    def get_ieee_company_id(self):
        """ Returns Infinidat's IEEE company ID """
        return self._data.ieee_company_id

    def get_system_serial(self):
        """ Returns the system serial number """
        return self._data.vendor_specific_identifier

    def get_volume_id(self):
        """ Returns the volume entity ID """
        return self._data.vendor_specific_identifier_extension

    def __str__(self):
        # return format as defined by http://tools.ietf.org/html/rfc3980#ref-FC-FS
        # e.g. naa.6742b0f000004e2b000000000000018c
        import binascii
        binary_without_header = binascii.hexlify(self._data.pack())[8:].decode('ASCII')
        return "naa." + binary_without_header

    def __repr__(self):
        return "<Infinidat NAA system {} volume {}>".format(self.get_system_serial(), self.get_volume_id())

    def _string_to_designator(self, descriptor):
        # supporting strings as returned from SCSI inquiry in the NAA designator
        # e.g. 6742b0f000004e2b000000000000018c (in hex)
        # we'll convert to NAA_IEEE_Registered_Extended_Designator and parse using create_from_string,
        # but we need to add DescriptorHeaderFields - we'll just add zeros
        raw_data = b"\x00\x00\x00" + struct.pack('b', len(descriptor)) + descriptor
        designator = designators.NAA_IEEE_Registered_Extended_Designator()
        designator.unpack(raw_data)
        return designator

    @classmethod
    def from_volume_id_and_system_serial(cls, volume_id, system_serial):
        # Concatenation of IEEE_company_id-24bit, reserved-20bit, system_id-16bit and volume_id-64bit
        descriptor = "6{:06x}{:05x}{:04x}{:016x}".format(NFINIDAT_IEEE, 0, system_serial, volume_id)
        return cls(descriptor.decode("hex"))
