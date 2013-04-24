class VendorSCSIBlockDevice(object):
    def __init__(self, device):
        super(VendorSCSIBlockDevice, self).__init__()
        self.device = device


class VendorSCSIStorageController(object):
    def __init__(self, device):
        super(VendorSCSIStorageController, self).__init__()
        self.device = device


class VendorSCSIEnclosureDevice(object):
    def __init__(self, device):
        super(VendorSCSIEnclosureDevice, self).__init__()
        self.device = device


class VendorMultipathBlockDevice(object):
    def __init__(self, device):
        super(VendorMultipathBlockDevice, self).__init__()
        self.device = device


class VendorMultipathStorageController(object):
    def __init__(self, device):
        super(VendorMultipathStorageController, self).__init__()
        self.device = device


class VendorFactoryImpl(object):
    def __init__(self):
        super(VendorFactoryImpl, self).__init__()
        self.vendor_mapping = {}  # (vid, pid) -> dict(block=class, controller=class, multipath=class)
        self._register_builtin_factories()

    def register(self, vid_pid, scsi_block_class, scsi_controller_class, scsi_enclosure_class,
                 multipath_block_class, multipath_controller_class):
        assert vid_pid not in self.vendor_mapping
        assert issubclass(scsi_block_class, VendorSCSIBlockDevice)
        assert issubclass(scsi_controller_class, VendorSCSIStorageController)
        assert issubclass(scsi_enclosure_class, VendorSCSIEnclosureDevice)
        assert issubclass(multipath_block_class, VendorMultipathBlockDevice)
        assert issubclass(multipath_controller_class, VendorMultipathStorageController)
        self.vendor_mapping[vid_pid] = dict(scsi_block=scsi_block_class, scsi_controller=scsi_controller_class,
                                            scsi_enclosure=scsi_enclosure_class,
                                            multipath_block=multipath_block_class,
                                            multipath_controller=multipath_controller_class)

    def _create_device_by_vid_pid(self, vid_pid, device_type, device):
        mapping = self.vendor_mapping.get(vid_pid)
        return None if mapping is None else mapping.get(device_type)(device)

    def create_scsi_block_by_vid_pid(self, vid_pid, device):
        return self._create_device_by_vid_pid(vid_pid, 'scsi_block', device)

    def create_scsi_controller_by_vid_pid(self, vid_pid, device):
        return self._create_device_by_vid_pid(vid_pid, 'scsi_controller', device)

    def create_scsi_enclosure_by_vid_pid(self, vid_pid, device):
        return self._create_device_by_vid_pid(vid_pid, 'scsi_enclosure', device)

    def create_multipath_block_by_vid_pid(self, vid_pid, device):
        return self._create_device_by_vid_pid(vid_pid, 'multipath_block', device)

    def create_multipath_controller_by_vid_pid(self, vid_pid, device):
        return self._create_device_by_vid_pid(vid_pid, 'multipath_controller', device)

    def _register_builtin_factories(self):
        from .infinidat.infinibox import mixin, vid_pid
        self.register(vid_pid, mixin.scsi_block_class, mixin.scsi_controller_class, mixin.scsi_enclosure_class,
                      mixin.multipath_block_class, mixin.multipath_controller_class)

VendorFactory = VendorFactoryImpl()
