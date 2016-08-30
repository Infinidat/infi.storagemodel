from infi.execute import execute_assert_success
from .scsi import AixModelMixin, AixSCSIBlockDevice
from .native_multipath import AixMultipathBlockDevice
from infi.storagemodel.errors import DeviceError

class AixRescan(AixModelMixin):
    def _add_new_devices(self):
        execute_assert_success(["cfgmgr"])

    def _get_all_devices(self, multipath):
        klass = AixSCSIBlockDevice if not multipath else AixMultipathBlockDevice
        devices = [klass(dev) for dev in self._get_dev_by_class("dac")] + \
                  [klass(dev) for dev in self._get_dev_by_class("disk")]

        multipath_devices = self._get_multipath_devices()
        filter_in = lambda dev: dev.get_display_name() in multipath_devices
        filter_out = lambda dev: dev.get_display_name() not in multipath_devices
        return list(filter(filter_in if multipath else filter_out, devices))

    def _do_report_luns(self, device_name):
        from infi.asi.executers import aix as aix_executer
        from infi.asi.coroutines.sync_adapter import sync_wait as _sync_wait
        from infi.asi.cdb.report_luns import ReportLunsCommand
        device = "/dev/{}" + device_name
        select_report = 0
        with aix_executer(device) as executer:
            command = ReportLunsCommand(select_report=int(select_report))
            result = _sync_wait(command.execute(executer))
            return result.lun_list

    def _remove_missing_scsi_devices(self):
        devices = self._get_all_devices(False)

        # go over all devices, build a dict that contains: hct -> dict of lun->device-name
        hcts = dict()
        for device in devices:
            hctl = device.get_hctl()
            hct = (hctl.get_host(), hctl.get_channel(), hctl.get_target())
            hct_luns = hcts[hct].setdefault(dict())
            hct_luns[hctl.get_lun()] = device.get_display_name()

        # do SCSI report luns on lun 0 of each hct, then remove the luns we see that are not returned
        for hct, hct_luns in hcts.values():
            lun0_device = hct_luns[0]       # LUN 0 must exist
            actual_luns = self._do_report_luns(lun0_device)
            missing_luns = set(hct_luns.keys()) - set(actual_luns)
            for missing_lun in missing_luns:
                dev_name = hct_luns[missing_lun]
                execute_assert_success(["rmdev", "-dl", dev_name])

    def _remove_missing_multipath_devices(self):
        devices = self._get_all_devices(True)
        for device in devices:
            try:
                # try to send an IO to make the OS refresh the state path
                device.get_scsi_standard_inquiry()
            except DeviceError:
                pass
            if all(path.get_state() == "down" for path in device.get_paths()):
                execute_assert_success(["rmdev", "-dl", device.get_display_name()])

    def rescan(self):
        self._add_new_devices()
        # TODO: The logic here is bad... We use information from the OS instead of checking the fabric itself.
        # for multipath devices we assume the "state" of the paths is updated
        # for scsi devices it's even worse, because we need 'get_hctl' when going over the devices, which uses
        # the ODM to find the target and LUN. This will fail for devices that are not defined - so for now
        # we don't remove missing SCSI devices and we assume the OS information is updated for multipath devices...
        # self._remove_missing_scsi_devices()
        self._remove_missing_multipath_devices()
