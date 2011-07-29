
from ..utils import cached_property, cached_method, clear_cache, LazyImmutableDict
from contextlib import contextmanager

class SupportedVPDPagesDict(LazyImmutableDict):
    def __init__(self, dict, device):
        super(SupportedVPDPagesDict, self).__init__(dict.copy())
        self.device = device

    def _create_value(self, page_code):
        from infi.asi.cdb.inquiry import SUPPORTED_VPD_PAGES_COMMANDS
        from infi.asi.coroutines.sync_adapter import sync_wait

        inquiry_command = SUPPORTED_VPD_PAGES_COMMANDS[page_code]()
        with self.device.asi_context() as asi:
            return sync_wait(inquiry_command.execute(asi))

class StorageModel(object):
    def __init__(self):
        super(StorageModel, self).__init__()

    @cached_property
    def scsi(self):
        return self._create_scsi_model()

    @cached_property
    def native_multipath(self):
        return self._create_native_multipath_model()

    def refresh(self):
        clear_cache(self)

    def _create_scsi_model(self):
        raise NotImplementedError()

    def _create_native_multipath(self):
        raise NotImplementedError()

class InquiryInformationMixin(object):
    @cached_property
    def scsi_vendor_id(self):
        return self.scsi_standard_inquiry.t10_vendor_identification

    @cached_property
    def scsi_product_id(self):
        return self.scsi_standard_inquiry.product_identification

    @cached_property
    def scsi_vid_pid(self):
        return (self.scsi_vendor_id, self.scsi_product_id)

    @cached_property
    def scsi_inquiry_pages(self):
        """Returns an immutable dict-like object of available inquiry pages from this device.
        For example:
        >>> dev.scsi_inquiry_pages[0x80].product_serial_number
        """
        from infi.asi.cdb.inquiry import INQUIRY_PAGE_SUPPORTED_VPD_PAGES
        from infi.asi.cdb.inquiry import SupportedVPDPagesInquiryCommand
        from infi.asi import AsiCheckConditionError
        from infi.asi.coroutines.sync_adapter import sync_wait
        command = SupportedVPDPagesInquiryCommand()

        page_dict = {}
        with self.asi_context() as asi:
            try:
                data = sync_wait(command.execute(asi))
                page_dict[INQUIRY_PAGE_SUPPORTED_VPD_PAGES] = data
                for page_code in data.vpd_parameters:
                    page_dict[page_code] = None
            except AsiCheckConditionError, e:
                # There are devices such as virtual USB disk controllers (bladecenter stuff) that don't support this
                # (mandatory!) command. In this case we simply return an empty dict.
                if e.sense_obj.sense_key == 'ILLEGAL_REQUEST' \
                   and e.sense_obj.additional_sense_code.code_name == 'INVALID FIELD IN CDB':
                    pass
                raise
        return SupportedVPDPagesDict(page_dict, self)

    @cached_property
    def scsi_serial_number(self):
        """Returns the SCSI serial of the device or an empty string ("") if not available"""
        from infi.asi.cdb.inquiry import INQUIRY_PAGE_UNIT_SERIAL_NUMBER
        serial = ''
        if INQUIRY_PAGE_UNIT_SERIAL_NUMBER in self.scsi_inquiry_pages:
            serial = self.scsi_inquiry_pages[INQUIRY_PAGE_UNIT_SERIAL_NUMBER].product_serial_number
        return serial

    @cached_property
    def scsi_standard_inquiry(self):
        with self.asi_context() as asi:
            command = StandardInquiryCommand()
            return sync_wait(command.execute(asi))

class SCSIDevice(object, InquiryInformationMixin):
    @contextmanager
    def asi_context(self):
        raise NotImplementedError()

    @cached_property
    def hctl(self):
        """returns a HCTL object"""
        raise NotImplementedError()


    @property
    def display_name(self):
        """returns a friendly device name.
        In Windows, its PHYSICALDRIVE%d, in linux, its sdX.
        """
        # platform implementation
        raise NotImplementedError

    @property
    def block_access_path(self):
        """returns a string path for the device
        In Windows, its something under globalroot
        In linux, its /dev/sdX"""
        raise NotImplementedError

    @property
    def scsi_access_path(self):
        """returns a string path for the device
        In Windows, its something under globalroot like block_device_path
        In linux, its /dev/sgX"""
        raise NotImplementedError

    @property
    def connectivity(self):
        """returns a mixin instance of this object and a connectivity interface"""
        # TODO connectivity factory, is it platform specific? for fiberchannel - yes, for iscsi???
        # Return either an iSCSIConnectivityInfo or FiberChannelConnectivityInfo
        from ..connectivity import ConnectivityFactory
        return ConnectivityFactory.create_mixin_object(self)

class SCSIBlockDevice(SCSIDevice):
    @property
    def size_in_bytes(self):
        # platform implementation
        raise NotImplementedError

    @property
    def vendor(self):
        """ Returns a vendor-specific implementation from the factory based on the device's SCSI vid and pid"""
        from ..vendor import VendorFactory
        return VendorFactory.create_block_by_vid_pid(self.scsi_vid_pid, self)

class SCSIStorageController(SCSIDevice):
    @property
    def vendor(self):
        """ Returns a vendor-specific implementation from the factory based on the device's SCSI vid and pid"""
        from ..vendor import VendorFactory
        return VendorFactory.create_controller_by_vid_pid(self.scsi_vid_pid, self)

class ScsiModel(object):
    def refresh_scsi_block_devices(self):
        clear_cache(self)

    def find_scsi_block_device_by_block_access_path(self, path):
        """return a SCSIBlockDevice object that matches the given path. raises KeyError if no such device is found"""
        devices_dict = dict([(device.block_access_path, device) for device in self.get_all_scsi_block_devices()])
        return devices_dict[path]

    def find_scsi_block_device_by_scsi_access_path(self, path):
        """return a SCSIBlockDevice object that matches the given path. raises KeyError if no such device is found"""
        devices_dict = dict([(device.scsi_access_path, device) for device in self.get_all_scsi_block_devices()])
        return devices_dict[path]

    def find_scsi_block_device_by_hctl(self, hctl):
        """return a SCSIBlockDevice object that matches the given hctl. raises KeyError if no such device is found"""
        devices_dict = dict([(device.hctl, device) for device in self.get_all_scsi_block_devices()])
        return devices_dict[hctl]

    def filter_vendor_specific_devices(self, devices, vid_pid_tuple):
        """returns only the items from the devices list that are of the specific type"""
        return filter(lambda x: x.scsi_vid_pid == vid_pid_tuple, devices)

    #############################
    # Platform Specific Methods #
    #############################

    @cached_method
    def get_all_scsi_block_devices(self):
        """
        Returns all SCSI block devices
          - Windows: Enumerate Disk Drives, Collecting SCSI devices that can work with SCSI_PASS_THROUGH.
               They can be either be multipath or non-multipath devices.
          - Linux:   we scan all the sd* (/sys/class/scsi_disk/*)
           - 
        """
        raise NotImplementedError

    def get_all_storage_controller_devices(self):
        """ Returns a list of SCSIStorageController objects.
        """
        raise NotImplementedError

    def rescan_and_wait_for(self, hctl_map, timeout_in_seconds=None):
        # TODO: I discussed this with rotem, he wants a different thing:
        # In this use-cas he's mapping a volume to volume onto a lun to an initiator port, and he wants to wait for
        # the mapping to wait. He wants to pass a list of (initiator_port, target_port, lun) and have us wait on these.
        # if initiator_port is None, we shall wait on each initiator_port we are aware of.
        # this is true for fiberchannel.
        # for iscsi the tuple is made of (initiator_iqn, initiator_ip, target_iqn, target_ip, lun).
        """ Rescan devices and wait for user-defined changes. Each key is an HCTL object and each value is True/False.
        True means the device should be mapped, False means that it should be unmapped.
        """
        raise NotImplementedError

class MultipathFrameworkModel(object):
    def get_devices(self):
        """ returns all multipath devices claimed by this framework
        """
        raise NotImplementedError

    def filter_non_multipath_scsi_block_devices(self, scsi_block_devices):
        """ returns items from the list that are not part of multipath devices claimed by this framework
        """
        raise NotImplementedError

    def filter_vendor_specific_devices(self, devices, vendor_mixin):
        """ returns only the items from the devices list that are of the specific type
        """
        return filter(lambda x: isinstance(x.vendor_specific_mixin, vendor_mixin), devices)

class NativeMultipathModel(MultipathFrameworkModel):
    pass

class MultipathDevice(object):
    @property
    def vendor(self):
        """ Returns a vendor-specific implementation from the factory based on the device's SCSI vid and pid"""
        return VendorFactory.create_multipath_by_vid_pid(self.scsi_vid_pid(), self)

    @property
    def device_path(self):
        """ linux: /dev/dm-X
        windows: mpiodisk%d
        """
        pass

    @property
    def display_name(self):
        """ linux: mpathX
        windows: physicaldrive
        """
        pass

    def with_asi_context(self):
        """ returns an asi object to the mulipath device itself
        """
        # TODO: do we get a context to one of the single-path devices or to the mpath device
        pass

    @property
    def scsi_serial_number(self):
        # TODO is it worth a while to have a base implemtation that gets it from page80 inquiry?
        raise NotImplementedError

    @property
    def scsi_standard_inquiry(self):
        """ there is no gurantee on which path this io goes on
        """
        # base implementation
        raise NotImplementedError

    @property
    def scsi_inquiry_pages(self):
        """ no warranty that all pages will be fetched from each path
        """
        # lazy fetch the list of supported pages. each __getitem__ will be then fetched.
        # e.g. scsi_inquiry_pages[0x80]
        # base implementation
        pass

    @property
    def size_in_bytes(self):
        # platform implementation
        raise NotImplementedError

    @property
    def paths(self):
        pass

    @property
    def policy(self):
        """ 'failover only', 'round robin', 'weighted round robin', 'least queue depth', 'least blocks',
        'round robin with subset'
        not all policies are supported on all platforms
        """
        # return a Policy object (FailOverOnly/Custom/...)

    @property
    def policy_attributes(self):
        """ names of path attributes relevant to this policy
        """
        pass

    def apply_policy(self, policy_builder):
        """
        linux: 
            failover only: group per path
            round-robin: all paths in one group, we ignore path states, weights
            weighted-paths: all paths in one group, allow weights
            round-robin with subset: not supported
            least queue depth: all paths in one group, selector is queue-length, not supported on all all distros
            least blocks: all paths in hour group, select is service-time, not supported on all distros
        windows: 
            round-robin with subset: not supported
            on invalid policy, ValueError is raised
            """
        pass

class FailoverOnlyBuilder(object):
    pass

class RoundRobinWithSubsetBuilder(object):
    def use_tpgs(self):
        return self


class Path(object):
    @property
    def path_id(self):
        """ sdX on linux, PathId on Windows
        """
        pass

    @property
    def hctl(self):
        pass

    @property
    def state(self):
        """ up/down
        """
        pass

# TODO the policy strategy
