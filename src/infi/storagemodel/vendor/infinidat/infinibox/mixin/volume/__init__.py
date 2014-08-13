from infi.pyutils.lazy import cached_method
from ..inquiry import InquiryException

from logging import getLogger
logger = getLogger(__name__)

class InfiniBoxVolumeMixin(object):
    @cached_method
    def _is_volume_mapped(self):
        """In race condition between a rescan and volume unmap operation, the device may still exist while the volume
        is already unampped. This method returns True if a volume is mapped to the device."""
        standard_inquiry = self.device.get_scsi_standard_inquiry()
        # spc4r30 section 6.4.2 tables 140 + 141, peripheral device type 0 is disk, 31 is unknown or no device
        return standard_inquiry.peripheral_device.type == 0

    @cached_method
    def get_volume_id(self):
        """ Returns the volume id within the InfiniBox """
        return self.get_naa().get_volume_id()

    @cached_method
    def get_volume_name(self):
        """ Returns the volume name inside the Infinibox, or None if not a volume """
        return self._get_volume_name_from_json_page()

    @cached_method
    def get_volume_type(self):
        """ Returns the volume type, or None if it is not a volume """
        raise NotImplementedError()

    def _get_volume_name_from_json_page(self):
        try:
            return self.get_string_data(0xc7)
        except InquiryException:
            return self._get_key_from_json_page('vol')
