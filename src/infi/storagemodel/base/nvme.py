from infi.pyutils.lazy import cached_method
from contextlib import contextmanager

from logging import getLogger


logger = getLogger(__name__)


class NVMEDevice(object):
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
        return "<{} {} for {} ({})>".format(self.__class__.__name__,
            self.get_scsi_access_path(), self.get_display_name(), self._get_scsi_serial_for_repr())