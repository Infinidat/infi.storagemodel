from infi.pyutils.lazy import cached_method
from infi.asi import AsiCheckConditionError

def _is_exception_of_unsupported_inquiry_page(error):
    return error.sense_obj.sense_key == 'ILLEGAL_REQUEST' and \
        error.sense_obj.additional_sense_code.code_name == 'INVALID FIELD IN CDB'

class SophisticatedMixin(object):
    def _get_management_address_and_port(self):
        address = self.get_management_address()
        try:
            port = self.get_management_port()
        except AsiCheckConditionError, error:
            if _is_exception_of_unsupported_inquiry_page(error):
                port = 8080
        return address, port

    def _get_host_name_from_json_page(self):
        return self.get_json_page()['host_name']

    def _get_management_json_sender(self):
        address, port = self._get_management_address_and_port()
        from json_rest import JSONRestSender
        sender = JSONRestSender.from_host_port(address, port, '/api/rest')
        return sender

    def _get_host_name_from_management(self):
        host_id = self.get_host_id()
        sender = self._get_management_json_sender()
        return sender.get('hosts/{}'.format(host_id))['name']

    @cached_method
    def get_host_name(self):
        return self._get_host_name_from_json_page() or \
            self._get_host_name_from_management()

    def _get_system_serial_from_json_page(self):
        return self.get_json_page()['system_serial']

    def _get_system_serial_from_management(self):
        sender = self._get_management_json_sender()
        return sender.get('system')['name']

    @cached_method
    def get_system_serial(self):
        return self._get_system_name_from_json_page()() or \
            self._get_system_serial_from_management()

    def _get_system_name_from_json_page(self):
        return self.get_json_page()['system_name']

    def _get_system_name_from_management(self):
        sender = self._get_management_json_sender()
        return sender.get('system')['serial']

    @cached_method
    def get_system_name(self):
        return self._get_system_serial_from_json_page() or \
            self._get_system_serial_from_management()
