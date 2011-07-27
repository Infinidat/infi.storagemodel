__import__("pkg_resources").declare_namespace(__name__)

class SCSIDevice(object):
    def with_asi(self):
        pass
    
    @proerty
    def hctl(self):
        pass
    
    @property
    def scsi_serial(self):
        # Returns the SCSI serial of the device or an empty string ("") if not available.
        pass

    @property
    def scsi_standard_inquiry(self):
        pass

    @property
    def scsi_inquiry_pages(self):
        # return an immutable dict-like object.
        # lazy fetch the list of supported pages. each __getitem__ will be then fetched.
        # e.g. scsi_inquiry_pages[0x80]
        pass
    
    @property
    def connectivity_info(self):
        # TODO: do we want this here? or just use the HCTL instead.
        # Return either an iSCSIConnectivityInfo or FiberChannelConnectivityInfo
        pass

    @property
    def display_name(self):
        pass

    @property
    def vendor_specific(self):
        # dev.vendor_specific.infi_volume
        pass

class LinuxSCSIDevice(object):
    @property
    def linux_sg_path(self):
        pass

class WindowsSCSIDevice(object):
    @property
    def win32_globalroot_path(self):
        pass
    
class SCSIBlockDevice(SCSIDevice):
    @property
    def size(self):
        pass

class WindowsSCSIBlockDevice(SCSIBlockDevice, WindowsSCSIDevice):
    @property
    def win32_physical_drive_path(self):
        pass
    
class LinuxSCSIBlockDevice(SCSIBlockDevice, LinuxSCSIDevice):
    @property
    def unix_devpath(self):
        pass
    
    @property
    def unix_devno(self):
        pass

    @property
    def linux_sd_path(self):
        pass

class SCSIStorageController(SCSIDevice):
    pass

class LinuxSCSIStorageController(SCSIStorageController, LinuxSCSIDevice):
    pass

class WindowsSCSIStorageController(SCSIStorageController, WindowsSCSIDevice):
    pass

class InfinidatSCSIBlockDeviceVendorInfo(object):
    @property
    def infi_volume_name(self):
        pass

    @property
    def infi_machine_ip(self):
        # Not really - just illustrating this.
        pass

def refresh_scsi_block_devices():
    """
    Clears the current device list so next time we'll read the device list from the OS.
    """
    pass


def get_all_scsi_block_devices():
    """
    Returns all SCSI block devices
      - Windows: Enumerate Disk Drives, Collecting SCSI devices that can work with SCSI_PASS_THROUGH
      - Linux:   we scan all the sd* (/sys/class/scsi_disk/*)
       - 
    SCSIBlockDevice:
      - pointer to sg
      - pointer to sd
    """
    pass

def find_scsi_block_device_by_devno(devno):
    pass

def find_scsi_block_device_by_path(path):
    pass

def find_scsi_block_device_by_hctl(hctl):
    pass

def get_all_storage_controller_devices():
    """
    Returns a list of SCSIStorageController/whatever objects.
    """
    pass

def rescan_and_wait_for(hctl_map, timeout_in_seconds=None):
    """
    Rescan devices and wait for user-defined changes. Each key is an HCTL object and each value is True/False.
    True means the device should be mapped, False means that it should be unmapped.
    """
    pass

#----
# native mpio impl
def get_all_native_mp_devices():
    pass

def filter_out_single_path_devices(device_list):
    pass


######
get_object_by_os('infi.storagemodel', 'store')

infi.storagemodel.linux.StorageModel
infi.storagemodel.windows.StorageModel

def get_storage_model():
    ddd
