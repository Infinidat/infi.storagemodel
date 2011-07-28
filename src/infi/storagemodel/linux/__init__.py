from .. import base

class LinuxSCSIDevice(object):
    @property
    def unix_devno(self):
        pass

class LinuxSCSIBlockDevice(base.SCSIBlockDevice, LinuxSCSIDevice):
    pass

class LinuxSCSIStorageController(base.SCSIStorageController, LinuxSCSIDevice):
    pass

class LinuxScsiModel(base.ScsiModel):
    pass

class LinuxNativeMultipathModel(base.NativeMultipathModel):
    pass

class LinuxStorageModel(StorageModel):
    def _create_scsi_model(self):
        return LinuxScsiModel()

    def _create_native_multipath_model(self):
        return LinuxNativeMultipathModel()
