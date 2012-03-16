
class InfinidatNAA(object):
    def __init__(self, data):
        super(InfinidatNAA, self).__init__()
        self._data = data

    def get_ieee_company_id(self):
        """:returns: Infinidat's IEEE company ID"""
        return (self._data.ieee_company_id__high << 20) + \
               (self._data.ieee_company_id__middle << 4) + \
               (self._data.ieee_company_id__low)

    def get_system_serial(self):
        """:returns: the system serial number"""
        return self._data.vendor_specific_identifier__low

    def get_volume_serial(self):
        """:returns: the volume entity ID"""
        return self._data.vendor_specific_identifier_extension

    def __repr__(self):
        return "<Infinidat NAA system {} volume {}".format(self.get_system_serial(), self.get_volume_serial())
