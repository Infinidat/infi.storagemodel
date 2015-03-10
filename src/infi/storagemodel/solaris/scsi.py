from contextlib import contextmanager
from ..base import scsi, gevent_wrapper
from infi.pyutils.lazy import cached_method
from infi.storagemodel.base.scsi import SCSIBlockDevice

MS = 1000
SG_TIMEOUT_IN_SEC = 3
SG_TIMEOUT_IN_MS = SG_TIMEOUT_IN_SEC * MS

class SolarisSCSIDeviceMixin(object):
    @contextmanager
    def asi_context(self):
        import os
        from infi.asi.unix import OSFile
        from infi.asi import create_platform_command_executer

        handle = OSFile(os.open(self.get_scsi_access_path(), os.O_RDWR))
        executer = create_platform_command_executer(handle, timeout=SG_TIMEOUT_IN_MS)
        executer.call = gevent_wrapper.defer(executer.call)
        try:
            yield executer
        finally:
            handle.close()

    @cached_method
    def get_scsi_access_path(self):
        return "/dev/rdsk/{}".format(self.device.get_device_name())

    @cached_method
    def get_scsi_vendor_id(self):
        return self.device.get_vendor().strip()

    @cached_method
    def get_scsi_revision(self):
        return self.device.get_revision().strip()

    @cached_method
    def get_scsi_product_id(self):
        return self.device.get_model().strip()


class SolarisSCSIBlockDeviceMixin(SolarisSCSIDeviceMixin):
    pass


class SolarisSCSIDevice(SolarisSCSIDeviceMixin, scsi.SCSIDevice):
    def __init__(self, device):
        super(SolarisSCSIDevice, self).__init__()
        self.device = device

    @cached_method
    def get_display_name(self):
        return self.device.get_scsi_device_name()


class SolarisSCSIBlockDevice(SolarisSCSIBlockDeviceMixin, scsi.SCSIBlockDevice):
    pass # TODO: Implement


class SolarisSCSIStorageController(SolarisSCSIDeviceMixin, scsi.SCSIStorageController):
    pass


class SolarisSCSIModel(scsi.SCSIModel):
    def __init__(se
