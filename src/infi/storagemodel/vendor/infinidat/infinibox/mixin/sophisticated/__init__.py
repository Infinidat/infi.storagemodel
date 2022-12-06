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
            logger.debug("key {} does not exist in JSON response".format(key))
            raise chain(InquiryException("KeyError: {}".format(key)))

    def _get_key_from_replication_json_page(self, key):
        if 0xcc in self.device.get_scsi_inquiry_pages():
            return self._get_key_from_json_page(key=key, page=0xcc)

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

    def _get_system_serial_from_json_page(self):
        try:
            return self._get_key_from_json_page('system_serial', 0xc6)
        except InquiryException:
            return self._get_key_from_json_page('system_serial')

    @cached_method
    def get_host_name(self):
        return self._get_host_name_from_json_page()

    @cached_method
    def get_cluster_name(self):
        return self._get_cluster_name_from_json_page()

    @cached_method
    def get_system_serial(self):
        return self._get_system_serial_from_json_page()

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

    # Active-Active and Mobility:
    def get_replication_mapping(self):
        """Return a mapping of system_serial -> (volume_id, volume_name, mobility_source) parsed from page 0xcc"""
        from collections import namedtuple
        ReplicationDataTuple = namedtuple('ReplicationDataTuple', ['id', 'name', 'mobility_source'])
        replication_page_data = self.get_json_data(0xcc)
        system_serials = replication_page_data['sys_serial']
        volume_ids = replication_page_data['vol_id']
        volume_names = replication_page_data['vol_name']
        if isinstance(replication_page_data['mobility_src'], bool):
            mobilitiy_sources = [replication_page_data['mobility_src'], not replication_page_data['mobility_src']]
        else:
            mobilitiy_sources = [None, None]
        return {system_serial: ReplicationDataTuple(volume_id, volume_name, mobility_source)
                for system_serial, volume_id, volume_name, mobility_source in
                zip(system_serials, volume_ids, volume_names, mobilitiy_sources)}

    def get_replication_type(self):
        return self._get_key_from_replication_json_page('rep_type')

    def get_mobility_source(self):
        return self._get_key_from_replication_json_page('mobility_src')

    def get_replication_system_serials(self):
        return self._get_key_from_replication_json_page('sys_serial')

    def get_replication_volume_ids(self):
        return self._get_key_from_replication_json_page('vol_id')

    def get_replication_volume_names(self):
        return self._get_key_from_replication_json_page('vol_name')
