
class VendorSCSIBlockDevice(object):
    def __init__(self, device):
        super(VendorSCSIBlockDevice, self).__init__()
        self.device = device

class VendorSCSIStorageController(object):
    def __init__(self, device):
        super(VendorSCSIStorageController, self).__init__()
        self.device = device

class VendorMultipathDevice(object):
    def __init__(self, device):
        super(VendorMultipathDevice, self).__init__()
        self.device = device

class VendorFactoryImpl(object):
    def __init__(self):
        super(VendorFactoryImpl, self).__init__()
        self.vendor_mapping = {} # (vid, pid) -> dict(block=class, controller=class, multipath=class)
        self._register_builtin_factories()

    def register(self, vid_pid, block_class, controller_class, multipath_class):
        assert vid_pid not in self.vendor_mapping
        assert issubclass(block_class, VendorSCSIBlockDevice)
        assert issubclass(controller_class, VendorSCSIStorageController)
        assert issubclass(multipath_class, VendorMultipathDevice)
        self.vendor_mapping[vid_pid] = dict(block=block_class, controller=controller_class, multipath=multipath_class)

    def _create_device_by_vid_pid(self, vid_pid, device_type, device):
        mapping = self.vendor_mapping.get(vid_pid)
        return None if map is None else mapping.get(device_type)(device)

    def create_block_by_vid_pid(self, vid_pid, device):
        return self._create_device_by_vid_pid(vid_pid, 'block', device)

    def create_controller_by_vid_pid(self, vid_pid, device):
        return self._create_device_by_vid_pid(vid_pid, 'controller', device)

    def create_multipath_by_vid_pid(self, vid_pid, device):
        return self._create_device_by_vid_pid(vid_pid, 'multipath', device)

    def _register_builtin_factories(self):
        from .infinidat.infinibox import mixin, vid_pid
        self.register(vid_pid, mixin.block_class, mixin.controller_class, mixin.multipath_class)

VendorFactory = VendorFactoryImpl()
