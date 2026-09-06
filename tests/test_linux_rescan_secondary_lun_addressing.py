from infi.pyutils.contexts import contextmanager



@contextmanager
def asi_context(*args, **kwargs):
    yield None

def sync_wait(*args, **kwargs):
    from infi.asi.cdb.report_luns import ReportLunsData
    raw = b'\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00\x40\x00\x00\x00\x00\x01\x00\x00\x40\x00\x00\x00\x00'
    data = ReportLunsData.create_from_string(raw)
    data.normalize_lun_list()
    return data

def test():
    from infi.storagemodel.base.gevent_wrapper import reinit
    from infi.storagemodel.linux.rescan_scsi_bus import logic, getters, scsi
    from mock import patch
    from unittest import SkipTest
    from os import name

    # why: keep this out of a module-level setUp(). nose runs module fixtures through
    # try_run(), which calls inspect.getargspec, and Python 3.11 removed it.
    if name == 'nt':
        raise SkipTest("this test covers the Linux rescan logic")
    reinit()

    with patch("infi.asi.coroutines.sync_adapter.sync_wait", new=sync_wait):
        with patch.object(logic, 'get_lun_type') as get_lun_type:
            with patch.object(logic, 'is_there_a_bug_in_sysfs_async_scanning', new=lambda: False):
                with patch.object(scsi, 'asi_context', new=asi_context):
                    with patch.object(logic, 'get_luns', return_value={1}):
                        with patch.object(logic, 'handle_add_devices') as handle_add_devices:
                            with patch.object(logic, 'handle_device_removal') as handle_device_removal:
                                get_lun_type.return_value = logic.STORAGE_ARRAY_CONTROLLER_DEVICE
                                logic.target_scan(0, 0, 0)
                                assert not handle_device_removal.called
