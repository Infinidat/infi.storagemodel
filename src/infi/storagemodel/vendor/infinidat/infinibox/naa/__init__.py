from .....errors import StorageModelError
from infi.asi.cdb.inquiry.vpd_pages.device_identification import designators

class InfinidatNAA(object):
    def __init__(self, data):
        super(InfinidatNAA, self).__init__()
        if isinstance(data, str):
            data = self._string_to_designator(data)
        if not isinstance(data, designators.NAA_IEEE_Registered_Extended_Designator):
            raise StorageModelError("Invalid argument type {!r}".format(data))
        self._data = data

    def get_ieee_company_id(self):
        """:returns: Infinidat's IEEE company ID"""
        return (self._data.ieee_company_id__high << 20) + \
               (self._data.ieee_company_id__middle << 4) + \
               (self._data.ieee_company_id__low)

    def get_system_serial(self):
        """:returns: the system serial number"""
        return self._data.vendor_specific_identifier__low

    def get_volume_id(self):
        """:returns: the volume entity ID"""
        return self._data.vendor_specific_identifier_extension

    def __str__(self):
        # return format as defined by http://tools.ietf.org/html/rfc3980#ref-FC-FS
        # e.g. naa.6742b0f000004e2b000000000000018c
        binary_without_header = str(self._data)[4:]
        return "naa." + binary_without_header.encode("hex")

    def __repr__(self):
        return "<Infinidat NAA system {} volume {}>".format(self.get_system_serial(), self.get_volume_id())

    def _string_to_designator(self, descriptor):
        # supporting strings as returned from SCSI inquiry in the NAA designator
        # e.g. 6742b0f000004e2b000000000000018c (in hex)
        # we'll convert to NAA_IEEE_Registered_Extended_Designator and parse using create_from_string,
        # but we need to add DescriptorHeaderFields - we'll just add zeros
        raw_data = "\x00\x00\x00" + chr(len(descriptor)) + descriptor
        designator = designators.NAA_IEEE_Registered_Extended_Designator.create_from_string(raw_data)
        return designator
