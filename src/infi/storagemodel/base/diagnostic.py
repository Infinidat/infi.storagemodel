from infi.pyutils.lazy import cached_method, LazyImmutableDict
from infi.storagemodel.errors import check_for_scsi_errors
#pylint: disable=E1002,W0622

__all__ = ['SesInformationMixin']


class SupportedSesPagesDict(LazyImmutableDict):
    """ An immutable dict-like object that is returned by the `SesInformationMixin` class """

    def __init__(self, page_dict, device, helper=None):
        super(SupportedSesPagesDict, self).__init__(page_dict.copy())
        self.device = device
        self.helper = helper

    @check_for_scsi_errors
    def _create_value(self, page_code):
        from infi.asi.cdb.diagnostic.ses_pages import get_ses_page
        from infi.asi.coroutines.sync_adapter import sync_wait
        with self.device.asi_context() as asi:
            diagnostic_command = get_ses_page(page_code)(self.helper) if self.helper else get_ses_page(page_code)()
            return sync_wait(diagnostic_command.execute(asi))

    def __repr__(self):
        return "<Supported SES Pages for {!r}: {!r}>".format(self.device, list(self.keys()))


class SesInformationMixin(object):
    """ Gets enclosure information from SCSI Enclosure Services (SES) """

    @cached_method
    @check_for_scsi_errors
    def get_scsi_ses_pages(self, helper=None):
        """Returns an immutable dict-like object of available SES pages from this device.
        """
        from infi.asi.cdb.diagnostic.ses_pages import DIAGNOSTIC_PAGE_SUPPORTED_PAGES
        from infi.asi.cdb.diagnostic.ses_pages import SupportedDiagnosticPagesCommand
        from infi.asi.coroutines.sync_adapter import sync_wait
        command = SupportedDiagnosticPagesCommand()

        page_dict = {}
        with self.asi_context() as asi:
            data = sync_wait(command.execute(asi))
            page_dict[DIAGNOSTIC_PAGE_SUPPORTED_PAGES] = data.supported_pages[:data.page_length]
            for page in range(data.page_length):
                page_dict[data.supported_pages[page]] = None
        return SupportedSesPagesDict(page_dict, self, helper)

    @cached_method
    def _get_configuration_page(self):
        from infi.asi.cdb.diagnostic.ses_pages import DIAGNOSTIC_PAGE_CONFIGURATION
        if DIAGNOSTIC_PAGE_CONFIGURATION in self.get_scsi_ses_pages():
            return self.get_scsi_ses_pages()[DIAGNOSTIC_PAGE_CONFIGURATION]

    @cached_method
    def get_enclosure_configuration_page(self):
        """Returns whole configuration page as a dict-like object"""
        return self._get_configuration_page()

    @cached_method
    def get_enclosure_configuration(self, raw_data=None):
        """
        Returns the dict of elements `{elem_type: (num_of_elem, elem_idx)}` where `elem_type` is
        the SES element code (see <http://en.wikipedia.org/wiki/SCSI_element_codes>)
        """
        from infi.asi.cdb.diagnostic.ses_pages import DIAGNOSTIC_PAGE_CONFIGURATION
        elements = {}
        if DIAGNOSTIC_PAGE_CONFIGURATION in self.get_scsi_ses_pages():
            conf_page = raw_data if raw_data else self._get_configuration_page()
            for subencl in range(len(conf_page.enclosure_descriptor_list)):
                for idx in range(len(conf_page.type_descriptor_header_list)):
                    elements[conf_page.type_descriptor_header_list[idx].element_type] = \
                        (conf_page.type_descriptor_header_list[idx].possible_elements_num, idx)
        return elements

    @cached_method
    def get_enclosure_vendor_specific_0x80(self):
        """Returns the vendor specific data dict from SES page 0x80"""
        from infi.asi.cdb.diagnostic.ses_pages import DIAGNOSTIC_PAGE_VENDOR_0X80
        if DIAGNOSTIC_PAGE_VENDOR_0X80 in self.get_scsi_ses_pages():
            vendor_data = self.get_scsi_ses_pages()[DIAGNOSTIC_PAGE_VENDOR_0X80].vendor_specific
        return vendor_data

    def _get_enclosure_elements_by_type(self, elem_type):
        """Returns a list of dicts per element according to element type, each dict is the element's status info"""
        from infi.asi.cdb.diagnostic.ses_pages import DIAGNOSTIC_PAGE_ENCLOSURE_STATUS
        from infi.asi.cdb.diagnostic.ses_pages import DIAGNOSTIC_PAGE_ELEMENT_DESCRIPTOR
        from infi.asi.cdb.diagnostic.ses_pages.enclosure_status import ELEMENT_STATUS_CODE
        elem_info = []
        if DIAGNOSTIC_PAGE_ENCLOSURE_STATUS in self.get_scsi_ses_pages():
            raw_conf_page = self._get_configuration_page()
            elements = self.get_enclosure_configuration(raw_conf_page)
            if elem_type in elements:
                num_of_elem, elem_idx = elements[elem_type]
                status_descr = \
                    self.get_scsi_ses_pages(raw_conf_page)[DIAGNOSTIC_PAGE_ENCLOSURE_STATUS].status_descriptors[elem_idx]
                for elem in status_descr.individual_elements:
                    d = dict(status=ELEMENT_STATUS_CODE[elem.element_status_code],
                             swap=elem.swap,
                             disabled=elem.disabled,
                             predicted_failure=elem.prdfail)
                    d.update(vars(elem.status_info))
                    elem_info.append(d)

        if DIAGNOSTIC_PAGE_ELEMENT_DESCRIPTOR in self.get_scsi_ses_pages():
            elem_descr = \
                self.get_scsi_ses_pages(raw_conf_page)[DIAGNOSTIC_PAGE_ELEMENT_DESCRIPTOR].element_descriptors[elem_idx]
            for idx, elem in enumerate(elem_descr.individual_elements):
                elem_info[idx].update(dict(descriptor=str(elem.descriptor)))

        return elem_info

    def get_all_enclosure_slots(self):
        """Returns a list of dicts per slot, each dict is the slot's status info"""
        from infi.asi.cdb.diagnostic.ses_pages.configuration import ELEMENT_TYPE_ARRAY_DEVICE_SLOT
        from infi.asi.cdb.diagnostic.ses_pages import DIAGNOSTIC_PAGE_ELEMENT_DESCRIPTOR
        slots = self._get_enclosure_elements_by_type(ELEMENT_TYPE_ARRAY_DEVICE_SLOT)
        if DIAGNOSTIC_PAGE_ELEMENT_DESCRIPTOR in self.get_scsi_ses_pages():
            for slot in slots:
                slot['location'] = int(slot['descriptor'].split()[1])
        return slots

    def get_all_enclosure_power_supply(self):
        """Returns a list of dicts per power supply, each dict is the power supply status info"""
        from infi.asi.cdb.diagnostic.ses_pages.configuration import ELEMENT_TYPE_POWER_SUPPLY
        ps = self._get_enclosure_elements_by_type(ELEMENT_TYPE_POWER_SUPPLY)
        return ps

    def get_all_enclosure_fans(self):
        """Returns a list of dicts per cooling element, each dict is the fan's status info"""
        from infi.asi.cdb.diagnostic.ses_pages.configuration import ELEMENT_TYPE_COOLING
        from infi.asi.cdb.diagnostic.ses_pages.enclosure_status import FAN_SPEED_CODE
        fans = self._get_enclosure_elements_by_type(ELEMENT_TYPE_COOLING)
        for fan in fans:
            fan['speed_code'] = FAN_SPEED_CODE[fan['speed_code']]
        return fans

    def get_all_enclosure_buzzers(self):
        """Returns a list of dicts per audible alarm element, each dict is the buzzer's status info"""
        from infi.asi.cdb.diagnostic.ses_pages.configuration import ELEMENT_TYPE_AUDIBLE_ALARM
        buzzer = self._get_enclosure_elements_by_type(ELEMENT_TYPE_AUDIBLE_ALARM)
        return buzzer

    def get_all_enclosure_temperature_sensors(self):
        """Returns a list of dicts per temperature sensor, each dict is the sensor's status info"""
        from infi.asi.cdb.diagnostic.ses_pages.configuration import ELEMENT_TYPE_TEMPERATURE_SENSOR
        temp_sensor = self._get_enclosure_elements_by_type(ELEMENT_TYPE_TEMPERATURE_SENSOR)
        return temp_sensor

    def get_all_enclosure_es_controllers(self):
        """Returns a list of dicts per ES controller, each dict is the controller's status info"""
        from infi.asi.cdb.diagnostic.ses_pages.configuration import ELEMENT_TYPE_ES_CONTROLLER
        es_cntrl = self._get_enclosure_elements_by_type(ELEMENT_TYPE_ES_CONTROLLER)
        return es_cntrl

    def get_all_enclosure_sas_expanders(self):
        """Returns a list of dicts per SAS expander, each dict is the expander's status info"""
        from infi.asi.cdb.diagnostic.ses_pages.configuration import ELEMENT_TYPE_SAS_EXPANDER
        sas_exp = self._get_enclosure_elements_by_type(ELEMENT_TYPE_SAS_EXPANDER)
        return sas_exp
