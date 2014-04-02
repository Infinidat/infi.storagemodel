from infi.pyutils.lazy import cached_method
from ..inquiry import InquiryException
from infi.exceptools import chain

from logging import getLogger
logger = getLogger(__name__)

class SophisticatedMixin(object):
    def _get_management_address_and_port(self):
        address = self.get_management_address()
        port = self.get_management_port()
        return address, port

    def _get_key_from_json_page(self, key, page=0xc5):
        try:
            return self.get_json_data(page)[key]
        except KeyError:
            logger.debug("key {} does not exists in JSON response".format(key))
            raise chain(InquiryException("KeyError: {}".format(key)))

    def _get_host_name_from_json_page(self):
        try:
            return self.get_string_data(0xc8)
        except InquiryException:
            return self._get_key_from_json_page('host')

    def _get_cluster_name_from_json_page(self):
        try:
            return self.get_string_data(0xc9)
        except InquiryException:
            return self._get_key_from_json_page('cluster')

    def _get_system_name_from_json_page(self):
        try:
            return self._get_key_from_json_page('system_name', 0xc6)
        except InquiryException:
            return self._get_key_from_json_page('system_name')

    def _get_system_version_from_json_page(self):
        try:
            return self._get_key_from_json_page('system_version', 0xc6)
        except InquiryException:
            return self._get_key_from_json_page('system_version')

    def _get_system_serial_from_naa(self):
        return self.get_naa().get_system_serial()

    @cached_method
    def get_host_name(self):
        return self._get_host_name_from_json_page()

    @cached_method
    def get_cluster_name(self):
        return self._get_cluster_name_from_json_page()

    @cached_method
    def get_system_serial(self):
        return self._get_system_serial_from_naa()

    @cached_method
    def get_system_name(self):
        return self._get_system_name_from_json_page()

    @cached_method
    def get_system_version(self):
        return self._get_system_version_from_json_page()
