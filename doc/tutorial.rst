
Getting Started
===============

To get started, first you need to get storage model:

    >>> from infi.storagemodel import get_storage_model
    >>> model = get_storage_model()

The model object is a global instance, so every time to call :func:`.get_storage_model()` you get the same instance.
Thus function returns an instance of :class:`.StorageModel`.

The storage model is layer-based. The first layer is the :ref:`scsi-layer`. Access to it is done by:

    >>> scsi = model.get_scsi()

The function is cached, so calling it again returns the same instance.

Now lets see what objects this gives us:

    >>> block_devices = scsi.get_all_scsi_block_devices()
    >>> target_controllers = scsi.get_all_storage_controller_devices()

These two functions, return all the 'seen' disks and controllers by the operating systems.
You can also ask for a specific device:

    >>> device = scsi.find_scsi_block_device_by_block_access_path("/dev/sda") # on Linux
    >>> device = scsi.find_scsi_block_device_by_scsi_access_path("/dev/sg0") # on Linux

and on Windows:

    >>> device = scsi.find_scsi_block_device_by_scsi_access_path(r"\\?\GLOBALROOT\Device\0000001a")

I hope you get it by now, everything is cached within the model, so if "/dev/sda" and "/dev/sg0" are actually the same
device, you'll get the same instance.

Also, you can get a device by its SCSI address:

    >>> from infi.dtypes.hctl import HCTL
    >>> device.find_scsi_block_device_by_hctl(HCTL(1,0,0,1))

These methods return either :class:`.SCSIStorageController` or :class:`.SCSIBlockDevice`, or lists of them.
Check their documentation to see what information they hold.

Now, lets get the multipath devices. In mose cases, we'd want to work with the native multipath driver,
:class:`.NativeMultipathModel`:

   >>> mpio = model.get_native_multipath()
   >>> devices = mpio.get_all_multipath_block_devices()

Usually, you'd also want to differ between the multipath disks and the non-multipath disks:

   >>> block_devices = scsi.get_all_scsi_block_devices()
   >>> mp_disks = mpio.get_all_multipath_block_devices()
   >>> non_mp_disks = mpio.filter_non_multipath_scsi_block_devices(block_devices)

Also, if you want disks of a specific product:

   >>> from infi.storagemodel.vendor.infinidat.infinibox import vid_pid
   >>> infinidat_mp_disks = mpio.filter_vendor_specific_devices(mp_disks, vid_pid)
   >>> infinidat_non_mp_disks  = mpio.filter_vendor_specific_devices(block_devices, vid_pid)

The :class:`.MultipathDevice` provides cross-platform abstraction of :class:`.Path` and their
:class:`.LoadBalancePolicy`. The platform-specific implementation translates the configurartion into the supported
:ref:`supported-policies`.


That's all for now.

Oh, check the :doc:`rescan` tutorial.
