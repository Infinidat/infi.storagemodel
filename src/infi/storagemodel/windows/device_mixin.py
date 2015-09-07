
from infi.pyutils.lazy import cached_method
from contextlib import contextmanager
from infi.wioctl.api import WindowsException
# pylint: disable=W0212,E1002

from infi.wioctl.errors import InvalidHandle
from infi.pyutils.decorators import wraps
from infi.exceptools import chain
from infi.storagemodel.errors import DeviceError
from infi.storagemodel.base.gevent_wrapper import defer
from logging import getLogger
logger = getLogger(__name__)

def replace_invalid_handle_with_device_error(func):
    @wraps(func)
    def catcher(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except InvalidHandle:
            raise chain(DeviceError())
    return catcher


class WindowsDeviceMixin(object):
    @cached_method
    def get_pdo(self):
        try:
            return defer(getattr)(self._device_object, 'psuedo_device_object')
        except KeyError:
            logger.exception("Getting device pdo raised KeyError")
            raise DeviceError()

    @contextmanager
    def asi_context(self):
        from infi.asi import create_platform_command_executer, create_os_file
        handle = create_os_file(self.get_pdo())
        executer = create_platform_command_executer(handle)
        executer.call = defer(executer.call)
        try:
            yield executer
        finally:
            handle.close()

    @cached_method
    @replace_invalid_handle_with_device_error
    def get_ioctl_interface(self):
        from infi.devicemanager.ioctl import DeviceIoControl
        return DeviceIoControl(self.get_pdo())

    @cached_method
    def get_instance_id(self):
        return self._device_object._instance_id

    @cached_method
    @replace_invalid_handle_with_device_error
    def get_hctl(self):
        from infi.dtypes.hctl import HCTL
        return HCTL(*defer(self.get_ioctl_interface().scsi_get_address)())

    @cached_method
    def get_parent(self):
        return self._device_object.parent

    @cached_method
    def _get_hwid(self):
        hwid = defer(getattr)(self._device_object, 'hardware_ids')[0]
        hwid = hwid.replace('SCSI\\Disk', '').replace('SCSI\\Array', '').replace('MPIO\\Disk', '')
        return hwid

    @cached_method
    def get_scsi_vendor_id(self):
        """Returns the stripped T10 vendor identifier string, as give in SCSI Standard Inquiry"""
        hwid = self._get_hwid()
        return hwid[:8].rstrip('_').replace('_', ' ')

    @cached_method
    def get_scsi_revision(self):
        """Returns the stripped T10 revision string, as give in SCSI Standard Inquiry"""
        hwid = self._get_hwid()
        return hwid[24:].rstrip('_').replace('_', ' ')

    @cached_method
    def get_scsi_product_id(self):
        """Returns the stripped T10 product identifier string, as give in SCSI Standard Inquiry"""
        hwid = self._get_hwid()
        return hwid[8:24].rstrip('_').replace('_', ' ')


class WindowsDiskDeviceMixin(object):
    @cached_method
    @replace_invalid_handle_with_device_error
    def get_size_in_bytes(self):
        return defer(self.get_ioctl_interface().disk_get_drive_geometry_ex)()

    @cached_method
    def get_physical_drive_number(self):
        """returns the drive number of the disk.
        if the disk is hidden (i.e. part of MPIODisk), it returns -1
        """
        try:
            number = defer(self.get_ioctl_interface().storage_get_device_number)()
            return -1 if number == 0xffffffff else number
        except WindowsException:
            return -1

    @cached_method
    def get_display_name(self):
        return "PHYSICALDRIVE%s" % self.get_physical_drive_number()

    @cached_method
    def get_block_access_path(self):
        from os import path
        number = self.get_physical_drive_number()
        if number == -1:
            return self.get_pdo()
        return '{sep}{sep}.{sep}PHYSICALDRIVE{number}'.format(sep=path.sep, number=self.get_physical_drive_number())

    @contextmanager
    def asi_context(self):
        from infi.asi import create_platform_command_executer, create_os_file
        handle = create_os_file(self.get_block_access_path())
        executer = create_platform_command_executer(handle)
        executer.call = defer(executer.call)
        try:
            yield executer
        finally:
            handle.close()
