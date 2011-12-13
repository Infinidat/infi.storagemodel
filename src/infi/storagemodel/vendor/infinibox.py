
from infi.pyutils.lazy import cached_method
from . import VendorMultipathDevice, VendorSCSIBlockDevice, VendorSCSIStorageController

from logging import getLogger
log = getLogger()

NFINIDAT_IEEE = 0x742B0F

class InfiniBoxMixin(object):
    @cached_method
    def get_box_management_address(self):
        """:returns: the management IPv4 address of the InfiniBox
        :rtype: string"""
        from infi.asi.cdb.inquiry.vpd_pages.device_identification.designators import VendorSpecificDesignator
        device_identification_page = self.device.get_scsi_inquiry_pages()[0x83]
        designators = device_identification_page.designators_list
        for designator in designators:
            log.debug("checking designator type %s %d of %d", designator.__class__.__name__,
                      designators.index(designator), len(designators))

            if isinstance(designator, VendorSpecificDesignator):
                value = designator.vendor_specific_identifier
                if value.startswith("ip"):
                    log.debug("SCSINameDesginator string = %r", value)
                    return value.split("=")[1].strip()

    @cached_method
    def get_box_management_port(self):
        """:returns: the management IPv4 port of the InfiniBox
        :rtype: string"""
        from infi.asi.cdb.inquiry.vpd_pages.device_identification.designators import VendorSpecificDesignator
        device_identification_page = self.device.get_scsi_inquiry_pages()[0x83]
        designators = device_identification_page.designators_list
        for designator in designators:
            log.debug("checking designator type %s %d of %d", designator.__class__.__name__,
                      designators.index(designator), len(designators))

            if isinstance(designator, VendorSpecificDesignator):
                value = designator.vendor_specific_identifier
                if value.startswith("port"):
                    log.debug("SCSINameDesginator string = %r", value)
                    return int(value.split("=")[1].strip())

    @cached_method
    def get_host_id(self):
        """:returns: the host id within the InfiniBox
        :rtype: int"""
        from infi.asi.cdb.inquiry.vpd_pages.device_identification.designators import VendorSpecificDesignator
        device_identification_page = self.device.get_scsi_inquiry_pages()[0x83]
        for designator in device_identification_page.designators_list:
            if isinstance(designator, VendorSpecificDesignator):
                value = designator.vendor_specific_identifier
                if value.startswith("host"):
                    return int(value.split("=")[1].strip())

    @cached_method
    def get_naa(self):
        """:returns: the infinidat naa
        :rtype: :class:`.InfinidatNAA`"""
        from infi.asi.cdb.inquiry.vpd_pages.device_identification import designators
        naa = designators.NAA_IEEE_Registered_Extended_Designator
        device_identification_page = self.device.get_scsi_inquiry_pages()[0x83]
        for designator in device_identification_page.designators_list:
            if isinstance(designator, naa):
                return InfinidatNAA(designator)

    @cached_method
    def get_target_port_group(self):
        """:returns: the target port group
        :rtype: int"""
        from infi.asi.cdb.inquiry.vpd_pages.device_identification.designators import TargetPortGroupDesignator
        device_identification_page = self.device.get_scsi_inquiry_pages()[0x83]
        for designator in device_identification_page.designators_list:
            if isinstance(designator, TargetPortGroupDesignator):
                return designator.target_port_group

    @cached_method
    def get_relative_target_port_group(self):
        """:returns: the relative target port group
        :rtype: int"""
        from infi.asi.cdb.inquiry.vpd_pages.device_identification.designators import RelativeTargetPortDesignator
        device_identification_page = self.device.get_scsi_inquiry_pages()[0x83]
        for designator in device_identification_page.designators_list:
            if isinstance(designator, RelativeTargetPortDesignator):
                return designator.relative_target_port_identifier

    @cached_method
    def get_fc_port(self):
        """:rtype: :class:`.InfinidatFiberChannelPort`"""
        return InfinidatFiberChannelPort(self.get_relative_target_port_group(),
                                         self.get_target_port_group())

    def _get_json_inquiry_page(self):
        from infi.asi.coroutines.sync_adapter import sync_wait
        with self.device.asi_context() as asi:
            inquiry_command = JSONInquiryPageCommand()
            return sync_wait(inquiry_command.execute(asi))

    @cached_method
    def get_json_data(self):
        """:returns: the json inquiry data from the system
        :rtype: dict"""
        from json import loads
        inquiry_page = self._get_json_inquiry_page()
        raw_data = inquiry_page.json_serialized_data
        return loads(raw_data)

from infi.instruct import UBInt8, UBInt16, Field, Struct
from infi.instruct.macros import VarSizeString
from infi.asi.cdb.inquiry import PeripheralDeviceData
from infi.asi.cdb.inquiry.vpd_pages import EVPDInquiryCommand

class JSONInquiryPageData(Struct):
    _fields_ = [
        Field("peripheral_device", PeripheralDeviceData),
        UBInt8("page_code"),
        VarSizeString("json_serialized_data", UBInt16)
    ]

class JSONInquiryPageCommand(EVPDInquiryCommand):
    def __init__(self):
        # pylint: disable=E1002
            # pylint: disable=E1002
        super(JSONInquiryPageCommand, self).__init__(0xc5, 1024, JSONInquiryPageData)

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

class InfinidatFiberChannelPort(object):
    def __init__(self, relative_target_port_identifer, target_port_group):
        super(InfinidatFiberChannelPort, self).__init__()
        self._relative_target_port_identifer = relative_target_port_identifer
        self._target_port_group = target_port_group

    def get_server_id(self):
        return (self._relative_target_port_identifer >> 8) & 0xff

    def get_port_id(self):
        return self._relative_target_port_identifer & 0xff

    def get_port_group(self):
        return self._target_port_group

# pylint: disable=C0103

class block_class(InfiniBoxMixin, InfiniBoxVolumeMixin, VendorSCSIBlockDevice):
    pass

class controller_class(InfiniBoxMixin, VendorSCSIStorageController):
    pass

class multipath_class(InfiniBoxMixin, InfiniBoxVolumeMixin, VendorMultipathDevice):
    pass

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

vid_pid = ("NFINIDAT" , "Infinidat A01")


class InfinidatVolumeExists(object):
    """A predicate that checks if an Infinidat volume exists"""
    def __init__(self, system_serial, volume_id):
        self.system_serial = system_serial
        self.volume_id = volume_id

    def __call__(self):
        from .. import get_storage_model
        model = get_storage_model()
        scsi = model.get_scsi()
        mpath = model.get_native_multipath()
        block_devices = scsi.filter_vendor_specific_devices(scsi.get_all_scsi_block_devices(), vid_pid)
        mp_devices = mpath.filter_vendor_specific_devices(mpath.get_all_multipath_devices(), vid_pid)
        non_mp_devices = mpath.filter_non_multipath_scsi_block_devices(block_devices)
        devices_to_query = mp_devices + non_mp_devices
        for device in devices_to_query:
            volume_id = device.get_vendor().get_naa().get_volume_serial()
            system_serial = device.get_vendor().get_naa().get_system_serial()
            log.debug("Found Infinidat volume id {} from system id {}".format(volume_id, system_serial))
        return any([self.volume_id == device.get_vendor().get_naa().get_volume_serial() and
                    self.system_serial == device.get_vendor().get_naa().get_system_serial() \
                    for device in devices_to_query])

class InfinidatVolumeDoesNotExist(InfinidatVolumeExists):
    """A predicate that checks if an Infinidat volume does not exist"""
    def __call__(self):
        return not super(InfinidatVolumeDoesNotExist, self).__call__()
