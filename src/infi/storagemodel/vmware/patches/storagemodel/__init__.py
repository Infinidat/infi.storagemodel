from infi.storagemodel.base import StorageModel, scsi, multipath, inquiry
from infi.pyutils.lazy import cached_method, LazyImmutableDict
from infi.pyutils.contexts import contextmanager
from infi.pyutils.patch import monkey_patch
from infi.asi.cdb.inquiry.vpd_pages import get_vpd_page_data
from infi.dtypes.hctl import HCTL
from time import time
from logging import getLogger
import infi.storagemodel

logger = getLogger(__name__)

PROPERTY_COLLECTOR_KEY = "infi.storagemodel.vmware.native_multipath"
SCSI_TOPOLOGY_PROPERTY_PATH = 'config.storageDevice.scsiTopology.adapter'
SCSI_LUNS_PROPERTY_PATH = "config.storageDevice.scsiLun"
MULTIPATH_TOPOLOGY_PROPERTY_PATH = 'config.storageDevice.multipathInfo.lun'


def install_property_collectors_on_client(client):
    from infi.pyvmomi_wrapper.property_collector import HostSystemCachedPropertyCollector
    if PROPERTY_COLLECTOR_KEY in client.property_collectors:
        return
    collector = HostSystemCachedPropertyCollector(client,
                                                  [SCSI_TOPOLOGY_PROPERTY_PATH, SCSI_LUNS_PROPERTY_PATH,
                                                   MULTIPATH_TOPOLOGY_PROPERTY_PATH])
    client.property_collectors[PROPERTY_COLLECTOR_KEY] = collector


def byte_array_to_string(byte_array):
    from infi.instruct import FixedSizeArray, Struct
    from infi import instruct
    class MyStruct(Struct):
        _fields_ = [FixedSizeArray("byte_array", len(byte_array), getattr(instruct, 'SBInt8')), ]
    struct = MyStruct(byte_array=byte_array)
    return struct.write_to_string(struct)


def number_to_ubint16_buffer(number):
    from infi.instruct import Struct
    from infi import instruct
    class MyStruct(Struct):
        _fields_ = [getattr(instruct, 'UBInt16')('number'), ]
    struct = MyStruct(number=number)
    return struct.write_to_string(struct)


def get_stack_trace():
    import sys
    try:
        raise ZeroDivisionError
    except ZeroDivisionError:
        return sys.exc_info()[2].tb_frame.f_back


@contextmanager
def with_host(client, host):
    from traceback import extract_stack
    from infi.pyvmomi_wrapper import get_reference_to_managed_object
    monkey_patch(infi.storagemodel, "get_storage_model", StorageModelFactory.get)
    previous = StorageModelFactory.get()
    stack_trace = get_stack_trace()
    caller = extract_stack(stack_trace, 6)[1][2]
    moref = get_reference_to_managed_object(host)
    try:
        current = StorageModelFactory.set(StorageModelFactory.create(client, host))
        if previous is current:
            logger.debug("entered context for the same host {} as part of {}".format(moref, caller))
        else:
            logger.debug("entered context for host {} as part of {}".format(moref, caller))
        yield
    finally:
        logger.debug("exited context for host {} as part of {}".format(moref, caller))
        StorageModelFactory.set(previous)


class VMwareHostStorageModel(StorageModel):
    def __init__(self, client, moref):
        super(VMwareHostStorageModel, self).__init__()
        self._moref = moref
        self._client = client
        self._install_property_collector()
        self._refresh_thread = None
        self._last_rescan_timestamp = 0

    def __repr__(self):
        try:
            return "<{}(moref={!r})>".format(self.__class__.__name__, self._moref)
        except:
            return super(VMwareHostStorageModel, self).__repr__()

    def _debug(self, message):
        logger.debug("{!r}: {}".format(self, message))

    def _refresh_host_storage(self, storage_system, reattach_luns=True, do_rescan=True, do_refresh=False):
        try:
            from urllib2 import URLError
        except ImportError:
            from urllib.error import URLError
        self._debug("_refresh_host_storage started, do_rescan={}, do_refresh={}".format(do_rescan, do_refresh))
        try:
            if do_rescan:
                storage_system.RescanAllHba()
                storage_system.RescanVmfs()
            if do_refresh:
                storage_system.RefreshStorageSystem()
            if reattach_luns:
                self._attach_detached_luns(storage_system)
            self._debug("_refresh_host_storage ended")
        except URLError:  # pragma: no cover
            # the storage_system calls above wait for completion and therefore may receive timeout exception
            # (in the form of URLError)
            # however we don't care if the tasks take longer than expected because this is _initiate_rescan only.
            # if we want to wait, we use the rescan_and_wait_for function
            self._debug("_refresh_host_storage caught URLError (timeout)")
        except:
            logger.exception("_refresh_host_storage caught an exception")
            raise   # hiding or no hiding the erros is handled in _initiate_rescan, according to 'raise_error'
        finally:
            self._last_rescan_timestamp = time()

    def retry_rescan(self, **rescan_kwargs):
        now = time()
        if (now - self._last_rescan_timestamp) > 30:
            self._initiate_rescan(**rescan_kwargs)
        else:
            self._debug("no point in retrying rescan in VMware as it takes too long, and it can take some time for the property collector to update")

    def _initiate_rescan(self, wait_for_completion=True, raise_error=False, do_rescan=True, do_refresh=False):
        from infi.storagemodel.base.gevent_wrapper import spawn, is_thread_alive
        host = self._client.get_managed_object_by_reference(self._moref)
        # we've seen several time in the tests that host.configManager is a list; how weird is that?
        # according to the API documntation, this is not a list; not sure how how to deal with this case
        # so for debugging, we do this:
        config_manager = host.configManager
        storage_system = config_manager.storageSystem
        if self._refresh_thread is not None and is_thread_alive(self._refresh_thread):
            self._debug("Skipping refresh - referesh thread is already active")
            if wait_for_completion:
                self._debug("Waiting for refresh thread to complete")
                if raise_error:
                    self._refresh_thread.get()       # this joins + raises exceptions if there were any
                else:
                    self._refresh_thread.join()
        else:
            self._refresh_thread = spawn(self._refresh_host_storage, storage_system, do_rescan=do_rescan, do_refresh=do_refresh)
            if wait_for_completion:
                self._debug("Waiting for refresh thread to complete")
                if raise_error:
                    self._refresh_thread.get()       # this joins + raises exceptions if there were any
                else:
                    self._refresh_thread.join()

    def rescan_and_wait_for(self, predicate=None, timeout_in_seconds=300, **rescan_kwargs):
        super(VMwareHostStorageModel, self).rescan_and_wait_for(predicate=predicate,
                                                                timeout_in_seconds=timeout_in_seconds,
                                                                **rescan_kwargs)

    def _create_scsi_model(self):
        return VMwareHostSCSIModel()

    def _create_native_multipath_model(self):
        return VMwareNativeMultipathModel(self._client, self._moref)

    def _create_veritas_multipath_model(self):
        return VMwareVeritasMultipathFrameworkModel(self._client, self._moref)

    def _create_mount_repository(self):
        StorageModel._create_mount_repository(self)

    def _install_property_collector(self):
        install_property_collectors_on_client(self._client)

    def _attach_detached_luns(self, storage_system):
        # sometimes new luns will be automatically detached if they were previously detached (the host remembers
        # that setting). If we still see a detached lun after rescan, we probably mapped it and want it attached.
        detached_luns = [lun.uuid for lun in storage_system.storageDeviceInfo.scsiLun if "off" in lun.operationalState]
        for lun in detached_luns:
            storage_system.AttachScsiLun(lun)
        if len(detached_luns) > 0:
            # rescan for VMFS volumes on the newly attached luns
            self._refresh_host_storage(storage_system, reattach_luns=False)


class VMwareInquiryPagesDict(LazyImmutableDict):
    def __init__(self, dict, scsi_lun_data_object):
        super(VMwareInquiryPagesDict, self).__init__(dict)
        self._scsi_lun_data_object = scsi_lun_data_object

    @cached_method
    def _get_peripheral_device(self):
        for durable_name in self._scsi_lun_data_object.alternateName:
            if durable_name.namespace == 'GENERIC_VPD':
                return byte_array_to_string([durable_name.data[0], ])

    def _build_device_identification_buffer(self, designators_list):
        size = sum(map(len, designators_list))
        return "{}\x83{}{}".format(self._get_peripheral_device(),
                                   number_to_ubint16_buffer(size),
                                   ''.join(designators_list))

    @cached_method
    def _get_dict_of_vpd_pages_and_their_raw_buffer(self):
        # http://vijava.sourceforge.net/vSphereAPIDoc/ver5/ReferenceGuide/
        vpd_dict = {}
        designators_list = []
        for durable_name in self._scsi_lun_data_object.alternateName:
            if durable_name.namespace == 'GENERIC_VPD':
                vpd = durable_name.data[1]
                vpd = vpd if vpd >= 0 else vpd + 256
                vpd_dict[vpd] = byte_array_to_string(durable_name.data)
            elif durable_name.namespace == 'SERIALNUM':
                buffer = byte_array_to_string(durable_name.data).rstrip('\x00')
                vpd_dict[0x80] = "{}\x80{}{}".format(self._get_peripheral_device(),
                                                     number_to_ubint16_buffer(len(buffer)),
                                                     buffer)
            else:
                designators_list.insert(-1, byte_array_to_string(durable_name.data))
        vpd_dict[0x83] = self._build_device_identification_buffer(designators_list)
        return vpd_dict

    def _create_value(self, key):
        buffer = self._get_dict_of_vpd_pages_and_their_raw_buffer()[key]
        page_buffer = get_vpd_page_data(key)()
        page_buffer.unpack(buffer)
        return page_buffer


class VMwareInquiryInformationMixin(inquiry.InquiryInformationMixin):
    @cached_method
    def get_scsi_product_id(self):
        return self._scsi_lun_data_object.model.strip()

    @cached_method
    def get_scsi_vendor_id(self):
        return self._scsi_lun_data_object.vendor.strip()

    def get_scsi_test_unit_ready(self):  # pragma: no cover
        pass

    @cached_method
    def get_scsi_standard_inquiry(self):  # pragma: no cover
        from infi.asi.cdb.inquiry.standard import StandardInquiryDataBuffer
        byte_array = self._scsi_lun_data_object.standardInquiry
        inquiry_buffer = StandardInquiryDataBuffer()
        inquiry_buffer.unpack(byte_array_to_string(byte_array))
        return inquiry_buffer

    def _get_supported_vpd_pages(self):
        from infi.asi.cdb.inquiry.vpd_pages.supported_pages import SupportedVPDPagesBuffer
        # http://vijava.sourceforge.net/vSphereAPIDoc/ver5/ReferenceGuide/vim.host.ScsiLun.DurableName.html
        def _filter(durable_name):
            return durable_name.namespace == 'GENERIC_VPD' and durable_name.namespaceId == 5 and \
                durable_name.data[1] == 0
        byte_array = list(filter(_filter, self._scsi_lun_data_object.alternateName)[0].data)
        page_buffer = SupportedVPDPagesBuffer()
        page_buffer.unpack(byte_array_to_string(byte_array))
        return page_buffer

    def get_scsi_inquiry_pages(self):
        supported_pages = self._get_supported_vpd_pages()
        pages_dict = {}
        for vpd_page in supported_pages.vpd_parameters[1:]:
            pages_dict[vpd_page] = None
        return VMwareInquiryPagesDict(pages_dict, self._scsi_lun_data_object)


class VMwarePath(multipath.Path):
    def __init__(self, client, host_moref, lun_key, path_data_object, properties):
        super(VMwarePath, self).__init__()
        self._client = client
        self._host_moref = host_moref
        self._lun_key = lun_key
        self._path_data_object = path_data_object
        self._properties = properties

    @cached_method
    def get_connectivity(self):
        """
        Returns an `infi.storagemodel.connectivity.FCConnectivity` instance.
        """
        from infi.storagemodel.connectivity import ConnectivityFactoryImpl
        return ConnectivityFactoryImpl().get_by_device_with_hctl(self)

    @cached_method
    def get_path_id(self):
        return self._path_data_object.name

    @cached_method
    def get_hctl(self):
        from infi.storagemodel.errors import RescanIsNeeded
        from pyVmomi import vim
        scsi_topology_adapters = self._properties.get(SCSI_TOPOLOGY_PROPERTY_PATH, [])
        expected_vmhba = self._path_data_object.adapter.split('-')[-1]
        # adapter.key is key-vim.host.ScsiTopology.Interface-vmhba0
        # path_data_object.adapter is key-vim.host.FibreChannelHba-vmhba2
        for adapter in [adapter for adapter in scsi_topology_adapters if adapter.key.split('-')[-1] == expected_vmhba]:
            for target in adapter.target:
                our_transport = self._path_data_object.transport
                target_transport = target.transport
                if (isinstance(our_transport, vim.HostInternetScsiTargetTransport) and
                    isinstance(target_transport, vim.HostInternetScsiTargetTransport) and
                    our_transport.iScsiName == target_transport.iScsiName) or \
                   (isinstance(our_transport, vim.HostFibreChannelTargetTransport) and
                    isinstance(target_transport, vim.HostFibreChannelTargetTransport) and
                    our_transport.portWorldWideName == target_transport.portWorldWideName):
                    for lun in target.lun:
                        # lun.scsiLun = "key-vim.host.ScsiLun-020c0000006742b0f000004e2b0000000000000000496e66696e69"
                        # self._lun_key = 'key-vim.host.ScsiDisk-02000200006742b0f000004e2b0000000000000069496e66696e69'
                        if lun.scsiLun.rsplit('-', 1)[-1] == self._lun_key.rsplit('-', 1)[-1]:
                            return HCTL(expected_vmhba, 0, target.target, lun.lun)
        logger.exception("failed to find SCSI target for path object {}".format(self._path_data_object))
        raise RescanIsNeeded()

    @cached_method
    def get_state(self):
        return self._path_data_object.state

    def get_alua_state(self):
        from pyVmomi import vim
        if self._path_data_object.state == vim.MultipathState.active:
            if self._path_data_object.isWorkingPath:
                return multipath.ALUAState.ACTIVE_OPTIMIZED
            else:
                return multipath.ALUAState.ACTIVE_NON_OPTIMIZED
        if self._path_data_object.state == vim.MultipathState.standby:
            return multipath.ALUAState.STANDBY
        return multipath.ALUAState.UNAVAILABLE


class VMwareMultipathDevice(VMwareInquiryInformationMixin):
    def __init__(self, client, host_moref, scsi_lun_data_object, properties):
        super(VMwareMultipathDevice, self).__init__()
        self._client = client
        self._host_moref = host_moref
        self._scsi_lun_data_object = scsi_lun_data_object
        self._properties = properties
        logger.debug("Created {!r}".format(self))

    @cached_method
    def get_display_name(self):
        return self._scsi_lun_data_object.displayName

    @cached_method
    def get_size_in_bytes(self):
        return self._scsi_lun_data_object.capacity.block * self._scsi_lun_data_object.capacity.blockSize

    def _get_multipath_logical_unit(self):
        from pyVmomi import vim
        # scsiLun.key == HostMultipathInfoLogicalUnit.lun
        host_luns = self._properties.get(MULTIPATH_TOPOLOGY_PROPERTY_PATH, [])
        try:
            return [lun for lun in host_luns if lun.lun == self._scsi_lun_data_object.key][0]
        except IndexError:
            msg = "No paths were found for device {}, returning an empty list"
            logger.error(msg.format(self._scsi_lun_data_object.key))
            return None

    @cached_method
    def get_paths(self):
        logical_unit = self._get_multipath_logical_unit()
        if logical_unit is None:
            return []
        return [VMwarePath(self._client, self._host_moref, self._scsi_lun_data_object.key,
                           path_data_object, self._properties)
                for path_data_object in logical_unit.path]

    @cached_method
    def get_uuid(self):  # pragma: no cover
        return self._scsi_lun_data_object.uuid

    @cached_method
    def get_canonical_name(self):
        return self._scsi_lun_data_object.canonicalName


class VMwareMultipathStorageController(VMwareMultipathDevice, multipath.MultipathStorageController):
    @cached_method
    def get_multipath_access_path(self):
        return self._scsi_lun_data_object.deviceName


class VMwareMultipathBlockDevice(VMwareMultipathDevice, multipath.MultipathBlockDevice):
    @cached_method
    def get_block_access_path(self):
        return self._scsi_lun_data_object.devicePath


class VMwareHostSCSIModel(scsi.SCSIModel):
    @cached_method
    def get_all_scsi_block_devices(self):
        # Everything in VMware is controlled by some Multipathing Plug-in
        return []

    @cached_method
    def get_all_storage_controller_devices(self):
        # Everything in VMware is controlled by some Multipathing Plug-in
        return []


class VMwareNativeMultipathModel(multipath.NativeMultipathModel):
    def __init__(self, client, moref):
        super(VMwareNativeMultipathModel, self).__init__()
        self._client = client
        self._moref = moref

    @cached_method
    def _get_properties(self):
        install_property_collectors_on_client(self._client)
        properties = self._client.property_collectors[PROPERTY_COLLECTOR_KEY].get_properties().get(self._moref, dict())
        return properties

    def _get_luns(self):
        return self._get_properties().get(SCSI_LUNS_PROPERTY_PATH, [])

    @cached_method
    def _filter_operating_luns(self):
        luns = self._get_luns()
        operating_luns = [lun for lun in luns if lun.operationalState[0] == 'ok']
        non_operating_luns = [lun for lun in luns if lun not in operating_luns]
        logger.debug("Non operating luns: {!r}".format(non_operating_luns))
        return operating_luns

    def _filter_array_controller_luns(self):
        return [lun for lun in self._filter_operating_luns() if lun.deviceType == 'array controller']

    def _filter_disk_luns(self):
        return [lun for lun in self._filter_operating_luns() if lun.deviceType == 'disk']

    @cached_method
    def get_all_multipath_storage_controller_devices(self):
        return [VMwareMultipathStorageController(self._client, self._moref,
                                                 scsi_lun_data_object, self._get_properties())
                for scsi_lun_data_object in self._filter_array_controller_luns()
                if scsi_lun_data_object.alternateName]

    @cached_method
    def get_all_multipath_block_devices(self):
        return [VMwareMultipathBlockDevice(self._client, self._moref,
                                           scsi_lun_data_object, self._get_properties())
                for scsi_lun_data_object in self._filter_disk_luns()
                if scsi_lun_data_object.alternateName]

    def filter_non_multipath_scsi_block_devices(self, scsi_block_devices):
        """ Returns an empty list since there no non-multipath devices on VMware """
        return list()

    def filter_non_multipath_scsi_storage_controller_devices(self, scsi_controller_devices):
        """ Returns an empty list since there no non-multipath devices on VMware """
        return list()


class VMwareVeritasMultipathFrameworkModel(multipath.NativeMultipathModel):
    def __init__(self, client, moref):
        super(VMwareVeritasMultipathFrameworkModel, self).__init__()
        self._client = client
        self._moref = moref

    @cached_method
    def get_all_multipath_block_devices(self):
        return []

    @cached_method
    def get_all_multipath_storage_controller_devices(self):
        return []

class StorageModelFactory(object):
    models_by_host_value = {}
    models_by_greenlet = {}

    @classmethod
    def clear(cls):
        cls.models_by_greenlet.clear()
        cls.models_by_host_value.clear()

    @classmethod
    def create(cls, client, hostsystem):
        from infi.pyvmomi_wrapper import get_reference_to_managed_object
        key = get_reference_to_managed_object(hostsystem)
        if (client, key) not in cls.models_by_host_value:
            value = VMwareHostStorageModel(client, key)
            cls.models_by_host_value[(client, key)] = value
        return cls.models_by_host_value[(client, key)]

    @classmethod
    def get_id(cls):
        from infi.storagemodel.base.gevent_wrapper import get_id
        return get_id()

    @classmethod
    def get(cls):
        return cls.models_by_greenlet.get(cls.get_id())

    @classmethod
    def set(cls, value):
        current = cls.get_id()
        if value is None:
            try:
                del cls.models_by_greenlet[current]
            except KeyError:
                pass
        else:
            cls.models_by_greenlet[current] = value
        return value
