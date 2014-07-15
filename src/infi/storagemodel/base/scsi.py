
from infi.pyutils.lazy import cached_method
from contextlib import contextmanager

from .inquiry import InquiryInformationMixin
from .diagnostic import SesInformationMixin
from logging import getLogger


logger = getLogger(__name__)


class SCSIDevice(InquiryInformationMixin, object):
    @cached_method
    def get_connectivity(self):
        """Returns a `infi.storagemodel.connectivity.FCConnectivity` instance."""
        from ..connectivity import ConnectivityFactory
        return ConnectivityFactory.get_by_device_with_hctl(self)

    #############################
    # Platform Specific Methods #
    #############################

    @contextmanager
    def asi_context(self):  # pragma: no cover
        """Returns a context for `infi.asi`"""
        # platform implementation
        raise NotImplementedError()

    @cached_method
    def get_hctl(self):  # pragma: no cover
        """Returns a `infi.dtypes.hctl.HCTL` object"""
        # platform implementation
        raise NotImplementedError()

    @cached_method
    def get_display_name(self):  # pragma: no cover
        """Returns a friendly device name. In Windows, it's PHYSICALDRIVE%d, in linux, its sdX."""
        # platform implementation
        raise NotImplementedError()

    @cached_method
    def get_scsi_access_path(self):  # pragma: no cover
        """Returns a string path for the device

                    - In Windows, it's something under globalroot like block_device_path
                    - In linux, it's /dev/sgX"""
        # platform implementation
        raise NotImplementedError()

    def _get_scsi_serial_for_repr(self):
        # we can't call get_scsi_serial_number because it may perform I/O which is wrapped with check_for_scsi_errors.
        # check_for_scsi_errors logs the scsi device, which calls this function and then we enter an infinite recursion.
        # Instead, if get_scsi_serial_number was already called, it will keep the serial number in self._serial, which
        # we try to get
        return getattr(self, "_serial", "<unknown-scsi-serial-number>")

    def __repr__(self):
        return "<SCSIDevice {} for {} ({})>".format(self.get_scsi_access_path(), self.get_display_name(),
                                                    self._get_scsi_serial_for_repr())


class SCSIBlockDevice(SCSIDevice):
    @cached_method
    def get_vendor(self):
        """Returns a get_vendor-specific implementation from the factory based on the device's SCSI vid and pid"""
        from ..vendor import VendorFactory
        return VendorFactory.create_scsi_block_by_vid_pid(self.get_scsi_vid_pid(), self)

    @cached_method
    def get_disk_drive(self):
        """Returns a `infi.storagemodel.base.disk.DiskDrive` object, or raises `infi.storagemodel.base.disk.NoSuchDisk`"""
        from infi.storagemodel import get_storage_model
        model = get_storage_model().get_disk()
        return model.find_disk_drive_by_block_access_path(self.get_block_access_path())

    @cached_method
    def get_block_access_path(self):  # pragma: no cover
        """Returns a string path for the device

                    - In Windows, it's something under globalroot
                    - In linux, it's /dev/sdX"""

        # platform implementation
        raise NotImplementedError()

    def __repr__(self):
        return "<SCSIBlockDevice: {} for {}>".format(self.get_block_access_path(),
                                                     super(SCSIBlockDevice, self).__repr__())

    #############################
    # Platform Specific Methods #
    #############################

    @cached_method
    def get_size_in_bytes(self):  # pragma: no cover
        # platform implementation
        raise NotImplementedError()


class SCSIStorageController(SCSIDevice):
    @cached_method
    def get_vendor(self):
        """ Returns a get_vendor-specific implementation from the factory based on the device's SCSI vid and pid"""
        from ..vendor import VendorFactory
        return VendorFactory.create_scsi_controller_by_vid_pid(self.get_scsi_vid_pid(), self)

    def __repr__(self):
        return "<SCSIStorageController {} for {}>".format(self.get_scsi_access_path(), self.get_display_name())


class SCSIEnclosure(SesInformationMixin, SCSIDevice):
    @cached_method
    def get_vendor(self):
        """ Returns a get_vendor-specific implementation from the factory based on the device's SCSI vid and pid"""
        from ..vendor import VendorFactory
        return VendorFactory.create_scsi_enclosure_by_vid_pid(self.get_scsi_vid_pid(), self)

    def __repr__(self):
        return "<SCSIEnclosure {} for {}>".format(self.get_scsi_access_path(), self.get_display_name())


class SCSIModel(object):
    def find_scsi_block_device_by_block_access_path(self, path):
        """Returns a `infi.storagemodel.base.scsi.SCSIBlockDevice` object that matches the given path.
        :raises: KeyError if no such device is found"""
        from infi.storagemodel.windows.scsi import WindowsSCSIBlockDevice
        devices_dict = dict([(device.get_block_access_path(), device) for device in self.get_all_scsi_block_devices()])
        for value in devices_dict.values():
            if isinstance(value, WindowsSCSIBlockDevice):
                devices_dict[r"\\.\{}".format(value.get_display_name())] = value
        return devices_dict[path]

    def find_scsi_block_device_by_scsi_access_path(self, path):
        """Returns `infi.storagemodel.base.scsi.SCSIBlockDevice` object that matches the given path.
        Raises `KeyError` if no such device is found."""
        devices_dict = dict([(device.get_scsi_access_path(), device) for device in self.get_all_scsi_block_devices()])
        return devices_dict[path]

    def find_scsi_block_device_by_hctl(self, get_hctl):
        """Returns a `infi.storagemodel.base.scsi.SCSIBlockDevice` object that matches the given get_hctl.
        Raises `KeyError` if no such device is found."""
        devices_dict = dict([(device.get_hctl(), device) for device in self.get_all_scsi_block_devices()])
        return devices_dict[get_hctl]

    def filter_vendor_specific_devices(self, devices, vid_pid_tuple):
        """Returns only the items from the devices list that are of the specific type"""
        return filter(lambda device: device.get_scsi_vendor_id_or_unknown_on_error() == vid_pid_tuple, devices)

    #############################
    # Platform Specific Methods #
    #############################

    @cached_method
    def get_all_scsi_block_devices(self):  # pragma: no cover
        """Returns a list of all `infi.storagemodel.base.scsi.SCSIBlockDevice`. Specifically, on:

        - Windows: Enumerate Disk Drives, Collecting SCSI devices that can work with SCSI_PASS_THROUGH.
          They can be either be multipath or non-multipath devices.
        - Linux: we scan all the sd\* (/sys/class/scsi_disk/\*)
        """
        # platform implementation
        raise NotImplementedError()

    @cached_method
    def get_all_storage_controller_devices(self):  # pragma: no cover
        """Returns a list of all `infi.storagemodel.base.scsi.SCSIStorageController` objects.
        """
        # platform implementation
        raise NotImplementedError()

    @cached_method
    def get_all_enclosure_devices(self):  # pragma: no cover
        """Returns a list of all `infi.storagemodel.base.scsi.SCSIEnclosure` objects.
        """
        # platform implementation
        raise NotImplementedError()
