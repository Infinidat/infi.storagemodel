from infi.pyutils.lazy import cached_method
from ..inquiry import InquiryException
from infi.exceptools import chain

from logging import getLogger
logger = getLogger(__name__)
DEFAULT_PORT = 80

class SophisticatedMixin(object):
    @cached_method
    def get_management_address(self):
        """ Returns the management IPv4 address of the InfiniBox as string """
        try:
            return self._get_key_from_json_page('ip', 0xcb)
        except InquiryException:
            return self.get_device_identification_page().get_vendor_specific_dict()['ip']

    @cached_method
    def get_management_port(self):
        """ Returns the management port number of the InfiniBox """
        try:
            return self._get_key_from_json_page('port', 0xcb)
        except InquiryException:
            vendor_specific_dict = self.get_device_identification_page().get_vendor_specific_dict()
        return int(vendor_specific_dict.get('port', str(DEFAULT_PORT)))

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
            return self._get_key_from_json_page('system_name', 0xcb) # x >= 1.5.0.14
        except InquiryException:
            try:
                return self._get_key_from_json_page('system_name', 0xc6) # 1.4 < x < 1.0.5.14
            except InquiryException:
                return self._get_key_from_json_page('system_name') # x <= 1.4

    def _get_system_version_from_json_page(self):
        try:
            return self._get_key_from_json_page('system_version', 0xc6)
        except InquiryException:
            return self._get_key_from_json_page('system_version')

    def _get_host_entity_id_from_json_page(self):
        try:
            return self._get_key_from_json_page('host_entity_id', 0xc6)
        except InquiryException:
            return self._get_key_from_json_page('host_entity_id')

    def _get_cluster_entity_id_from_json_page(self):
        try:
            return self._get_key_from_json_page('cluster_entity_id', 0xc6)
        except InquiryException:
            return self._get_key_from_json_page('cluster_entity_id')

    def _get_pool_id_from_json_page(self):
        try:
            return self._get_key_from_json_page('pool_id', 0xc6)
        except InquiryException:
            return self._get_key_from_json_page('pool_id')

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

    @cached_method
    def get_host_id(self):
        return self._get_host_entity_id_from_json_page()

    @cached_method
    def get_cluster_id(self):
        return self._get_cluster_entity_id_from_json_page()

    @cached_method
    def get_pool_id(self):
        return self._get_pool_id_from_json_page()

    @cached_method
    def get_pool_name(self):
        return self.get_string_data(page=0xca)
