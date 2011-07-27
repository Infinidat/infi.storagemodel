__import__("pkg_resources").declare_namespace(__name__)

class StorageModel(object):
    __instances__ = dict()

    @property
    def platform(self):
        from platform import system
        return system().lower().replace('-', '')

    @property
    def scsi(self):
        if not StorageModel.__instances__.has_key("scsi"):
            exec "from .%s import ScsiModel"
            StorageModel.__instances__["scsi"] = ScsiModel()
        return self.__instances__["scsi"]

    @property
    def native_multipath(self):
        if not StorageModel.__instances__.has_key("native_multipath"):
            exec "from .%s import NativeMultipathModel" % self.platform
            StorageModel.__instances__["native_multipath"] = NativeMultipathModel()
        return self.__instances__["native_multipath"]

def infinidat_devlist_example():
    model = StorageModel()
    scsi_block_devices = model.scsi.get_all_scsi_block_devices()
    mp_devices = model.native_multipath.get_devices()
    non_mp_devices = model.native_multipath.filter_non_multipath_scsi_block_devices(scsi_block_devices)

    from .vendor_specific import VendorSpecificFactory
    infibox = VendorSpecificFactory().get_mixin_class_by_vid_pid("NFINIDAT", "InfiniBox")

    for device in model.native_multipath.filter_vendor_specific_devices(mp_devices, infibox):
        print "\t".join([device.display_name, device.device_path, device.vendor_specific_mixin.volume_name])
        mp_devices.pop(device)

    for device in model.scsi.filter_vendor_specific_devices(non_mp_devices, infibox):
        print "\t".join([device.display_name, device.deivce_path, device.size_in_bytes])
        non_mp_devices.pop(device)