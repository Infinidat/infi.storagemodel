import struct
from .....errors import StorageModelError
from .. import NFINIDAT_IEEE
from infi.asi.cdb.inquiry.vpd_pages import designators
from infi.instruct.buffer import be_uint_field, bytes_ref


class InfinidatDesignator(designators.Buffer):
    naa = be_uint_field(where=(bytes_ref[0].bits[4:8]))
    ieee_company_id = be_uint_field(where=(bytes_ref[1].bits[4:8] + bytes_ref[0].bits[0:4] +
                                           bytes_ref[2].bits[4:8] + bytes_ref[1].bits[0:4] +
                                           bytes_ref[3].bits[4:8] + bytes_ref[2].bits[0:4]))
    system_serial = be_uint_field(where=(bytes_ref[6:8]))
    volume_id = be_uint_field(where=bytes_ref[8:16])


class InfinidatNAA(object):
    def __init__(self, data):
        super(InfinidatNAA, self).__init__()
        if isinstance(data, (str, bytes)):
            data = self._string_to_designator(data)
        elif not isinstance(data, designators.NAA_IEEE_Registered_Extended_Designator):
            data = self._string_to_designator(data.pack())[4:]
        elif not isinstance(data, InfinidatDesignator):
            pass
        else:
            raise StorageModelError("Invalid argument type {!r}".format(data))
        self._data = data

    def get_ieee_company_id(self):
        """ Returns Infinidat's IEEE company ID """
        return self._data.ieee_company_id

    def get_system_serial(self):
        """ Returns the system serial number """
        return self._data.system_serial

    def get_volume_id(self):
        """ Returns the volume entity ID """
        return self._data.volume_id

    def __str__(self):
        # return format as defined by http://tools.ietf.org/html/rfc3980#ref-FC-FS
        # e.g. naa.6742b0f000004e2b000000000000018c
        import binascii
        binary_without_header = binascii.hexlify(self._data.pack()).decode('ASCII')
        return "naa." + binary_without_header

    def __repr__(self):
        return "<Infinidat NAA system {} volume {}>".format(self.get_system_serial(), self.get_volume_id())

    def _string_to_designator(self, descriptor):
        # supporting strings as returned from SCSI inquiry in the NAA designator
        # e.g. 6742b0f000004e2b000000000000018c (in hex)
        # we'll convert to NAA_IEEE_Registered_Extended_Designator and parse using create_from_string,
        # but we need to add DescriptorHeaderFields - we'll just add zeros
        designator = InfinidatDesignator()
        designator.unpack(descriptor)
        return designator

    @classmethod
    def from_volume_id_and_system_serial(cls, volume_id, system_serial):
        # Concatenation of IEEE_company_id-24bit, reserved-20bit, system_id-16bit and volume_id-64bit
        descriptor = "6{:06x}{:05x}{:04x}{:016x}".format(NFINIDAT_IEEE, 0, system_serial, volume_id)
        return cls(descriptor.decode("hex"))
