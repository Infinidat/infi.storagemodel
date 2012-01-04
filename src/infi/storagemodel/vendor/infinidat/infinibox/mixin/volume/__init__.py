from infi.pyutils.lazy import cached_method

class InfiniBoxVolumeMixin(object):
    @cached_method
    def _is_volume_mapped(self):
        """In race condition between a rescan and volume unmap operation, the device may stil exists while there volume
        is already unampped.
        :returns: this method returns True if a volume is mapped to the device."""
        standard_inquiry = self.device.get_scsi_standard_inquiry()
        # spc4r30 section 6.4.2 tables 140 + 141, peripheral device type 0 is disk, 31 is unknown or no device
        return standard_inquiry.peripheral_device.type == 0

    @cached_method
    def get_volume_id(self):
        """:returns: the volume name within the InfiniBox
        :rtype: int"""
        return self.get_naa().get_volume_serial()

    @cached_method
    def get_volume_name(self):
        return self._get_volume_name_from_json_page() or self._get_volume_name_from_management()

    def _get_volume_name_from_json_page(self):
        return self.get_json_data()['volume_name']

    def _get_volume_name_from_management(self):
        volume_id = self.get_volume_id()
        sender = self._get_management_json_sender()
        return sender.get('volumes/{}'.format(volume_id))['name']
