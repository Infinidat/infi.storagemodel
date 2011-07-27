
from .. import base

class WindowsSCSIDevice(object):
    pass

class WindowsSCSIBlockDevice(base.SCSIBlockDevice, WindowsSCSIDevice):
    pass

class WindowsSCSIStorageController(base.SCSIStorageController, WindowsSCSIDevice):
    pass

class ScsiModel(base.ScsiModel):
    pass

class NativeMultipathModel(base.NativeMultipathModel):
    pass
