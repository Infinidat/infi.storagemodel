
from .. import base

class WindowsSCSIDevice(object):
    @property
    def win32_globalroot_path(self):
        pass

class WindowsSCSIBlockDevice(base.SCSIBlockDevice, WindowsSCSIDevice):
    @property
    def win32_physical_drive_path(self):
        pass

class WindowsSCSIStorageController(base.SCSIStorageController, WindowsSCSIDevice):
    pass

class ScsiModel(base.ScsiModel):
    pass

class NativeMultipathModel(base.NativeMultipathModel):
    pass
