
from .. import base

class LinuxSCSIDevice(object):
    @property
    def unix_devno(self):
        pass

class LinuxSCSIBlockDevice(base.SCSIBlockDevice, LinuxSCSIDevice):
    pass

class LinuxSCSIStorageController(base.SCSIStorageController, LinuxSCSIDevice):
    pass

class ScsiModel(base.ScsiModel):
    pass

class NativeMultipathModel(base.NativeMultipathModel):
    pass
