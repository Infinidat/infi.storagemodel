from infi.pyutils.lazy import cached_method
from ..inquiry import JSONInquiryException
from infi.exceptools import chain

from logging import getLogger
logger = getLogger(__name__)

class SophisticatedMixin(object):
    def _get_management_address_and_port(self):
        address = self.get_management_address()
        port = self.get_management_port()
        return address, port

    def _get_key_from_json_page(self, key):
        try:
            return self.get_json_data()[key]
        except KeyError:
            logger.debug("key {} does not exists in JSON response".format(key))
            raise chain(JSONInquiryException("KeyError: {}".format(key)))

    def _get_host_name_from_json_page(self):
        return self._get_key_from_json_page('host')

    def _get_cluster_name_from_json_page(self):
        return self._get_key_from_json_page('cluster')

    def _get_management_json_sender(self):
        address, port = self._get_management_address_and_port()
        from json_rest import JSONRestSender
        sender = JSONRestSender.from_host_port(address, port, '/api/rest')
        return sender

    def _get_host_name_from_management(self):
        host_id = self.get_host_id()
        sender = self._get_management_json_sender()
        return None if host_id == -1 or host_id == 0 else sender.get('hosts/{}'.format(host_id))['name']

    def _get_cluster_name_from_management(self):
        cluster_id = self.get_cluster_id()
        sender = self._get_management_json_sender()
        return None if cluster_id == -1 or cluster_id == 0 else sender.get('clusters/{}'.format(cluster_id))['name']

    @cached_method
    def get_host_name(self):
        try:
            return self._get_host_name_from_json_page()
        except JSONInquiryException:
            return self._get_host_name_from_management()

    @cached_method
    def get_cluster_name(self):
        try:
            return self._get_cluster_name_from_json_page()
        except JSONInquiryException:
            return self._get_cluster_name_from_management()

    def _get_system_serial_from_naa(self):
        return self.get_naa().get_system_serial()

    def _get_system_serial_from_json_page(self):
        return self._get_key_from_json_page('system_serial')

    def _get_system_serial_from_management(self):
        sender = self._get_management_json_sender()
        return sender.get('system')['serial']

    @cached_method
    def get_system_serial(self):
        return self._get_system_serial_from_naa()

    def _get_system_name_from_json_page(self):
        return self._get_key_from_json_page('system_name')

    def _get_system_name_from_management(self):
        sender = self._get_management_json_sender()
        return sender.get('system')['name']

    @cached_method
    def get_system_name(self):
        try:
            return self._get_system_name_from_json_page()
        except JSONInquiryException:
            return self._get_system_name_from_management()
