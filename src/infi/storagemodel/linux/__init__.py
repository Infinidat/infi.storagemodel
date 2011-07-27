
from .. import base

class LinuxSCSIDevice(object):
    @property
    def linux_sg_path(self):
        pass

class LinuxSCSIBlockDevice(base.SCSIBlockDevice, LinuxSCSIDevice):
    @property
    def unix_devpath(self):
        pass

    @property
    def unix_devno(self):
        pass

    @property
    def linux_sd_path(self):
        pass

class LinuxSCSIStorageController(base.SCSIStorageController, LinuxSCSIDevice):
    pass

class ScsiModel(base.ScsiModel):
    pass

class NativeMultipathModel(base.NativeMultipathModel):
    pass
