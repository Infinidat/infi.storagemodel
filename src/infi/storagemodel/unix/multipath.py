from infi.storagemodel.errors import check_for_scsi_errors

class UnixPathMixin(object):

    @check_for_scsi_errors
    def get_alua_state(self):
        from infi.asi.cdb.rtpg import RTPGCommand
        from infi.asi.cdb.inquiry.vpd_pages.device_identification import DeviceIdentificationVPDPageCommand
        from infi.asi.coroutines.sync_adapter import sync_wait
        rtpg_command = RTPGCommand()
        device_identification_command = DeviceIdentificationVPDPageCommand()
        with self.asi_context() as asi:
            rtpg_result = sync_wait(rtpg_command.execute(asi))
            device_identification_result = sync_wait(device_identification_command.execute(asi))
        target_port_group = device_identification_result.designators_list[-1].target_port_group
        [device_alua_state] = [descriptor.asymetric_access_state for descriptor in rtpg_result.descriptor_list
                               if descriptor.target_port_group == target_port_group]
        return device_alua_state
