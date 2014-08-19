from infi.storagemodel.base import StorageModel, scsi, multipath, inquiry
from infi.pyutils.lazy import cached_method, LazyImmutableDict
from infi.pyutils.contexts import contextmanager
from infi.pyutils.patch import monkey_patch
from infi.asi.cdb.inquiry.vpd_pages import get_vpd_page_data
from infi.dtypes.hctl import HCTL
from logging import getLogger
import infi.storagemodel

logger = getLogger(__name__)

PROPERTY_COLLECTOR_KEY = "infi.storagemodel.vmware.native_multipath"
SCSI_TOPOLOGY_PROPERTY_PATH = 'config.storageDevice.scsiTopology'
SCSI_LUNS_PROPERTY_PATH = "config.storageDevice.scsiLun"
MULTIPATH_TOPOLOGY_PROPERTY_PATH = 'config.storageDevice.multipathInfo'


def install_property_collectors_on_client(client):
    from pyvisdk.facade.property_collector import HostSystemCachedPropertyCollector
    if PROPERTY_COLLECTOR_KEY in client.facades:
        return
    collector = HostSystemCachedPropertyCollector(client,
                                                  [SCSI_TOPOLOGY_PROPERTY_PATH, SCSI_LUNS_PROPERTY_PATH,
                                                   MULTIPATH_TOPOLOGY_PROPERTY_PATH])
    client.facades[PROPERTY_COLLECTOR_KEY] = collector



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


def format_stack_trace(f, limit=None):
    import cStringIO
    import traceback
    sio = cStringIO.StringIO()
    traceback.print_stack(f, limit=limit, file=sio)
    s = sio.getvalue()
    sio.close()
    if s[-1:] == "\n":
        s = s[:-1]
    return s


@contextmanager
def with_host(host):
    from traceback import extract_stack
    monkey_patch(infi.storagemodel, "get_storage_model", StorageModelFactory.get)
    previous = StorageModelFactory.get()
    stack_trace = get_stack_trace()
    caller = extract_stack(stack_trace, 6)[1][2]
    moref = host.core.getReferenceToManagedObject(host)
    try:
        current = StorageModelFactory.set(StorageModelFactory.create(host))
        if previous is current:
            formatted_stacktrace = format_stack_trace(stack_trace)
            logger.debug("entered context for the same host {} as part of {}:\nTraceback:\n{}".format(moref, caller, formatted_stacktrace))
        else:
            logger.debug("entered context for host {} as part of {}".format(moref, caller))
        yield
    finally:
        logger.debug("exited context for host {} as part of {}".format(moref, caller))
        StorageModelFactory.set(previous)


class VMwareHostStorageModel(StorageModel):
    def __init__(self, pyvisdk_client, moref):
        super(VMwareHostStorageModel, self).__init__()
        self._moref = moref
        self._client = pyvisdk_client
        self._install_property_collector()

    def _refresh_host_storage(self, storage_system):
        storage_system.RescanAllHba()
        storage_system.RescanVmfs()
        storage_system.RefreshStorageSystem()

    def initiate_rescan(self, wait_for_completion=False):
        from urllib2 import URLError
        # we've seen several time in the tests that host.configManager is a list; how weird is that?
        # so for debugging, we do this:
        moref = self._moref
        host = self._client.getManagedObjectByReference(moref)
        config_manager = host.configManager
        # according to the API documntation, this is not a list; not sure how how to deal with this case
        summary = host.summary
        storage_system = config_manager.storageSystem
        try:
            self._refresh_host_storage(storage_system)
        except URLError:  # pragma: no cover
            # the calls above wait for completion and therefore may receive timeout exception (in the form of URLError)
            # however we don't care if the tasks take longer than expected because this is initiate_rescan only
            # if we want to wait, we use the rescan_and_wait_for function
            pass
        self._attach_detached_luns(storage_system)

    def _create_scsi_model(self):
        return VMwareHostSCSIModel()

    def _create_native_multipath_model(self):
        return VMwareNativeMultipathModel(self._client, self._moref)

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
            self._refresh_host_storage(storage_system)


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
        from infi.asi.cdb.inquiry.standard import StandardInquiryData
        byte_array = self._scsi_lun_data_object.standardInquiry
        buffer = byte_array_to_string(byte_array)
        return StandardInquiryData.create_from_string(buffer)

    def _get_supported_vpd_pages(self):
        from infi.asi.cdb.inquiry.vpd_pages.supported_pages import SupportedVPDPagesBuffer
        # http://vijava.sourceforge.net/vSphereAPIDoc/ver5/ReferenceGuide/vim.host.ScsiLun.DurableName.html
        def _filter(durable_name):
            return durable_name.namespace == 'GENERIC_VPD' and durable_name.namespaceId == 5 and \
                durable_name.data[1] == 0
        byte_array = filter(_filter, self._scsi_lun_data_object.alternateName)[0].data
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
    def __init__(self, pyvisdk_client, host_moref, lun_key, path_data_object):
        super(VMwarePath, self).__init__()
        self._client = pyvisdk_client
        self._host_moref = host_moref
        self._lun_key = lun_key
        self._path_data_object = path_data_object

    @cached_method
    def get_path_id(self):
        return self._path_data_object.name

    @cached_method
    def _get_properties(self):
        # We want to use the data the entire model uses, so we read from cache
        install_property_collectors_on_client(self._client)
        properties = self._client.facades[PROPERTY_COLLECTOR_KEY].getProperties()[self._host_moref]
        return properties

    @cached_method
    def get_hctl(self):
        from infi.storagemodel.errors import RescanIsNeeded
        scsi_topology = self._get_properties()[SCSI_TOPOLOGY_PROPERTY_PATH]
        expected_vmhba = self._path_data_object.adapter.split('-')[-1]
        # adapter.key is key-vim.host.ScsiTopology.Interface-vmhba0
        # path_data_object.adapter is key-vim.host.FibreChannelHba-vmhba2
        for adapter in filter(lambda adapter: adapter.key.split('-')[-1] == expected_vmhba,
                              scsi_topology.adapter):
            for target in adapter.target:
                if self._path_data_object.transport.portWorldWideName == target.transport.portWorldWideName:
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


class VMwareMultipathDevice(VMwareInquiryInformationMixin):
    def __init__(self, pyvisdk_client, host_moref, scsi_lun_data_object):
        super(VMwareMultipathDevice, self).__init__()
        self._client = pyvisdk_client
        self._host_moref = host_moref
        self._scsi_lun_data_object = scsi_lun_data_object
        logger.debug("Created {!r}".format(self))

    @cached_method
    def get_display_name(self):
        return self._scsi_lun_data_object.displayName

    @cached_method
    def get_size_in_bytes(self):
        return self._scsi_lun_data_object.capacity.block * self._scsi_lun_data_object.capacity.blockSize

    @cached_method
    def _get_properties(self):
        # We want to use the data the entire model uses, so we read from cache
        install_property_collectors_on_client(self._client)
        properties = self._client.facades[PROPERTY_COLLECTOR_KEY].getProperties()[self._host_moref]
        return properties

    def _get_multipath_logical_unit(self):
        # scsiLun.key == HostMultipathInfoLogicalUnit.lun
        host_luns = self._get_properties()[MULTIPATH_TOPOLOGY_PROPERTY_PATH].lun
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
        return [VMwarePath(self._client, self._host_moref, self._scsi_lun_data_object.key, path_data_object)
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
    def __init__(self, pyvisdk_client, moref):
        super(VMwareNativeMultipathModel, self).__init__()
        self._client = pyvisdk_client
        self._moref = moref

    @cached_method
    def _get_properties(self):
        install_property_collectors_on_client(self._client)
        properties = self._client.facades[PROPERTY_COLLECTOR_KEY].getProperties()[self._moref]
        return properties

    def _get_luns(self):
        return self._get_properties()[SCSI_LUNS_PROPERTY_PATH]

    @cached_method
    def _filter_operating_luns(self):
        luns = self._get_luns()
        operating_luns = [lun for lun in luns if lun.operationalState[0] == 'ok']
        non_operating_luns = [lun for lun in luns if lun not in operating_luns]
        logger.debug("Non operating luns: {!r}".format(non_operating_luns))
        return operating_luns

    def _filter_array_controller_luns(self):
        return filter(lambda lun: lun.deviceType == 'array controller',
                      self._filter_operating_luns())

    def _filter_disk_luns(self):
        return filter(lambda lun: lun.deviceType == 'disk',
                      self._filter_operating_luns())

    @cached_method
    def get_all_multipath_storage_controller_devices(self):
        return [VMwareMultipathStorageController(self._client, self._moref, scsi_lun_data_object)
                for scsi_lun_data_object in self._filter_array_controller_luns()
                if scsi_lun_data_object.alternateName]

    @cached_method
    def get_all_multipath_block_devices(self):
        return [VMwareMultipathBlockDevice(self._client, self._moref, scsi_lun_data_object)
                for scsi_lun_data_object in self._filter_disk_luns()
                if scsi_lun_data_object.alternateName]

    def filter_non_multipath_scsi_block_devices(self, scsi_block_devices):
        """ Returns an empty list since there no non-multipath devices on VMware """
        return list()

    def filter_non_multipath_scsi_storage_controller_devices(self, scsi_controller_devices):
        """ Returns an empty list since there no non-multipath devices on VMware """
        return list()


class StorageModelFactory(object):
    models_by_host_value = {}
    models_by_greenlet = {}

    @classmethod
    def clear(cls):
        cls.models_by_greenlet.clear()
        cls.models_by_host_value.clear()

    @classmethod
    def create(cls, hostsystem):
        key = hostsystem.ref.value
        if key not in cls.models_by_host_value:
            value = VMwareHostStorageModel(hostsystem.core, "HostSystem:{}".format(key))
            cls.models_by_host_value[key] = value
        return cls.models_by_host_value[key]

    @classmethod
    def get_id(cls):
        try:
            from gevent import getcurrent
            return getcurrent()
        except ImportError:
            from thread import get_ident
            return get_ident()

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
