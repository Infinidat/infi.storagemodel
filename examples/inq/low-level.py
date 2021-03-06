from platform import system
from infi.pyutils.contexts import contextmanager


@contextmanager
def asi_context(access_path):
    import os

    operating_system = system()

    if operating_system == 'Windows':
        from infi.asi.win32 import OSFile, Win32CommandExecuter
        handle = OSFile(access_path)
        executer = Win32CommandExecuter(handle)
    else:
        from infi.asi.unix import OSFile
        handle = OSFile(os.open(access_path, os.O_RDWR))

        if operating_system == 'SunOS':
            from infi.asi.solaris import SolarisCommandExecuter
            executer = SolarisCommandExecuter(handle)
        elif operating_system == 'linux':
            from infi.asi.linux import LinuxIoctlCommandExecuter
            executer = LinuxIoctlCommandExecuter(handle)

    try:
        yield executer
    finally:
        handle.close()


def get_scsi_standard_inquiry(access_path):
    from infi.asi.coroutines.sync_adapter import sync_wait
    from infi.asi.cdb.inquiry.standard import StandardInquiryCommand, STANDARD_INQUIRY_MINIMAL_DATA_LENGTH

    with asi_context(access_path) as asi:
        command = StandardInquiryCommand(allocation_length=STANDARD_INQUIRY_MINIMAL_DATA_LENGTH)
        result = sync_wait(command.execute(asi))
        return result


def get_scsi_serial(access_path):
    from infi.asi.coroutines.sync_adapter import sync_wait
    from infi.asi.cdb.inquiry.vpd_pages.unit_serial_number import UnitSerialNumberVPDPageCommand

    with asi_context(access_path) as asi:
        command = UnitSerialNumberVPDPageCommand()
        try:
            result = sync_wait(command.execute(asi))
        except:
            return ''
        return result.product_serial_number


def get_capacity_in_bytes(access_path):
    from infi.asi.coroutines.sync_adapter import sync_wait
    from infi.asi.cdb.read_capacity import ReadCapacity16Command

    with asi_context(access_path) as asi:
        command = ReadCapacity16Command()
        try:
            result = sync_wait(command.execute(asi))
        except:
            return ''
        return result.last_logical_block_address * result.block_length_in_bytes


def get_devices():
    from glob import glob

    def windows():
        from infi.devicemanager import DeviceManager
        from infi.devicemanager.ioctl import DeviceIoControl
        drive_numbers = [DeviceIoControl(disk_drive.psuedo_device_object).storage_get_device_number() for
                         disk_drive in DeviceManager().disk_drives]
        return [r"\\.\PHYSICALDRIVE{0}".format(drive_number) for
                drive_number in drive_numbers if
                drive_number != -1]

    def linux():
        sd = sorted(dev for dev in glob("/dev/sd*") if not dev[-1].isdigit())
        dm = sorted(glob("/dev/dm*"))
        return sd + dm

    def solaris():
        rdsk = sorted(glob("/dev/rdsk/c*"))
        return rdsk

    return dict(Windows=windows, Linux=linux, SunOS=solaris).get(system(), lambda: [])()


def main():
    inq_format = "{:<16}:{:<8}:{:<16}:{:<4}:{:<32}:{:>12}"
    devices = get_devices()
    print inq_format.format("DEVICE", "VEND", "PROD", "REV", "SER NUM", "CAP(kb)     ")
    for access_path in devices:
        try:
            inquiry_data = get_scsi_standard_inquiry(access_path)
            scsi_serial = get_scsi_serial(access_path)
            capacity = get_capacity_in_bytes(access_path)
        except:
            continue
        print inq_format.format(access_path,
                                inquiry_data.t10_vendor_identification, inquiry_data.product_identification,
                                inquiry_data.product_revision_level,
                                scsi_serial, capacity)


if __name__ == "__main__":
    main()
