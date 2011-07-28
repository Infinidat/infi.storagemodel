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
    def find_scsi_block_device_by_devno(self, devno):
        """ raises KeyError if not found. devno is type of str.
        on linux: by major/minor
        on windows: by number of physicaldrive
        """
        # TODO this is not cross-platform, should it be in here?
        raise NotImplementedError

class LinuxNativeMultipathModel(base.NativeMultipathModel):
    pass

class LinuxStorageModel(base.StorageModel):
    def _create_scsi_model(self):
        return LinuxScsiModel()

    def _create_native_multipath_model(self):
        return LinuxNativeMultipathModel()

