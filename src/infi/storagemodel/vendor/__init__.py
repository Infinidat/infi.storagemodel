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

class VendorFactory(object):
    def __init__(self):
        super(VendorSpecificFactoryImpl, self).__init__()
        self.vendor_mapping = {} # (vid, pid) -> dict(block=class, controller=class, multipath=class)

    def register(vid_pid, block_class, controller_class, multipath_class):
        assert vid_pid not in self.vendor_mapping
        assert issubclass(block_class, VendorSCSIBlockDevice)
        assert issubclass(controller_class, VendorSCSIStorageController)
        assert issubclass(multipath_class, VendorMultipathDevice)
        self.vendor_mapping[vid_pid] = dict(block=block_class, controller=controller_class, multipath=multipath_class)

    def create_block_by_vid_pid(vid_pid, device):
        assert vid_pid in self.vendor_mapping
        return self.vendor_mapping[vid_pid]['block'](device)

    def create_controller_by_vid_pid(vid_pid, device):
        assert vid_pid in self.vendor_mapping
        return self.vendor_mapping[vid_pid]['controller'](device)

    def create_multipath_by_vid_pid(vid_pid, device):
        assert vid_pid in self.vendor_mapping
        return self.vendor_mapping[vid_pid]['multipath'](device)
