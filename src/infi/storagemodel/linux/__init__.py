from ..base import StorageModel, scsi, multipath

class LinuxSCSIDevice(object):
    @property
    def unix_devno(self):
        pass

class LinuxSCSIBlockDevice(scsi.SCSIBlockDevice, LinuxSCSIDevice):
    pass

class LinuxSCSIStorageController(scsi.SCSIStorageController, LinuxSCSIDevice):
    pass

class LinuxScsiModel(scsi.SCSIModel):
    def find_scsi_block_device_by_devno(self, devno):
        """ raises KeyError if not found. devno is type of str.
        on linux: by major/minor
        on windows: by number of physicaldrive
        """
        # TODO this is not cross-platform, should it be in here?
        raise NotImplementedError

class LinuxNativeMultipathModel(multipath.NativeMultipathModel):
    pass

class LinuxStorageModel(StorageModel):
    def _create_scsi_model(self):
        return LinuxScsiModel()

    def _create_native_multipath_model(self):
        return LinuxNativeMultipathModel()

