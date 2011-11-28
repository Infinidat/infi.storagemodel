from infi.pyutils.lazy import cached_method

class LinuxBlockDeviceMixin(object):
    @cached_method
    def get_block_access_path(self):
        return "/dev/%s" % self.sysfs_device.get_block_device_name()

    @cached_method
    def get_unix_block_devno(self):
        return self.sysfs_device.get_block_devno()

    @cached_method
    def get_size_in_bytes(self):
        return self.sysfs_device.get_size_in_bytes()
