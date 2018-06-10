'''

## Getting Started

To get started, first you need to get an `infi.storagemodel.base.StorageModel` instance:

    #!python
    from infi.storagemodel import get_storage_model
    model = get_storage_model()

The storagemodel object is a global instance, so every call to `get_storage_model` returns the same instance.


### Working with SCSI devices

The storage model is layer-based. The first layer is the [SCSI layer](base/scsi.m.html). Access to it is done by:

    #!python
    scsi = model.get_scsi()

The function is cached, so calling it again returns the same `infi.storagemodel.base.scsi.SCSIModel` instance.

Now let's see what objects this gives us:

    #!python
    block_devices = scsi.get_all_scsi_block_devices()
    target_controllers = scsi.get_all_storage_controller_devices()

These two functions return all the disks and controllers that are visible to the operating system.
You can also ask for a specific device:

    #!python
    device = scsi.find_scsi_block_device_by_block_access_path("/dev/sda")
    device = scsi.find_scsi_block_device_by_scsi_access_path("/dev/sg0")

and on Windows:

    #!python
    device = scsi.find_scsi_block_device_by_scsi_access_path(r"\\?\GLOBALROOT\Device\0000001a")

As with the rest of the API everything is cached within the model, so if "/dev/sda" and "/dev/sg0" are actually the same
device, you'll get the same instance.

You can also get a device by its SCSI address:

    #!python
    from infi.dtypes.hctl import HCTL
    device.find_scsi_block_device_by_hctl(HCTL(1,0,0,1))

These methods return either `infi.storagemodel.base.scsi.SCSIStorageController` or `infi.storagemodel.base.scsi.SCSIBlockDevice`,
or lists of them. Check their documentation to see what information they hold.


### Working with multipath devices

Now, let's get the multipath devices. In mose cases, we'd want to work with the native multipath driver,
`infi.storagemodel.base.multipath.NativeMultipathModel`:

    #!python
    mpio = model.get_native_multipath()
    devices = mpio.get_all_multipath_block_devices()

Typically you'd also want to differentiate between the multipath disks and the non-multipath ones:

    #!python
    block_devices = scsi.get_all_scsi_block_devices()
    mp_disks = mpio.get_all_multipath_block_devices()
    non_mp_disks = mpio.filter_non_multipath_scsi_block_devices(block_devices)

If you want disks of a specific product only:

    #!python
    from infi.storagemodel.vendor.infinidat.infinibox import vid_pid
    infinidat_mp_disks = mpio.filter_vendor_specific_devices(mp_disks, vid_pid)
    infinidat_non_mp_disks  = mpio.filter_vendor_specific_devices(block_devices, vid_pid)

The `infi.storagemodel.base.multipath.MultipathDevice` provides cross-platform abstraction of `infi.storagemodel.base.multipath.Path`
and their `infi.storagemodel.base.multipath.LoadBalancePolicy`. The platform-specific implementation translates the
configuration into the supported :ref:`supported-policies`.


## Scanning for changes in Storage

Doing a rescan on the SCSI bus is an expensive operation.

Usually, issuing a rescan on an operating system does not report on comlpetion,
and it takes some time for the upper layers to finish their work.

Since rescan is usually done when there's a change in connectivity or mapping, storagemodel
provides an interfaces that blocks until an expected condition is met.

The method `rescan_and_wait_for` accepts a predicate and blocks until the predicate returns `True`, or timeout is raised.

Let's see some examples.


### Waiting for a new device

The most common use case is that a volume has been mapped, and you want to wait for it to appear.

Waiting for a new disk is straightforward using the `infi.storagemodel.predicates.DiskExists` predicate:

    #!python
    from infi.storagemodel import get_storage_model
    from infi.storagemodel.predicates import DiskExists
    get_storage_model().rescan_and_wait_for(DiskExists("123456"))

This predicate works for both multipath disks and non-multipath disks


### Waiting for a device to be gone

If you want to rescan after unmapping a volume, use the `infi.storagemodel.predicates.DiskNotExists` predicate.


### Fiber Channel mappings

If you performed a connectivity change, you can wait for it to happen.

    #!python
    from infi.storagemodel.predicates import FiberChannelMappingExists
    predicate = FiberChannelMappingExists("01020304060708", "0a:0b:0c:0d:0e:0f:0g:0h", 0)
    get_storage_model().rescan_and_wait_for(predicate)

This predicate needs three arguments: the initiator WWN, the target WWN and the LUN.

WWNs can be formatted however you like - lowercase, uppercase, with separators or without them.

See `infi.storagemodel.predicates.FiberChannelMappingExists` and `infi.storagemodel.predicates.FiberChannelMappingNotExists`.


### Waiting for several conditions

You can also wait for several conditions together:

    #!python
    from infi.storagemodel.predicates import DiskExists, DiskNotExists, PredicateList
    predicates = PredicateList([DiskExists("123"), DiskNotExists("456")])
    get_storage_model().rescan_and_wait_for(predicates)


'''

__import__("pkg_resources").declare_namespace(__name__)

__all__ = ['get_storage_model']

__storage_model = None

from logging import getLogger
from infi.exceptools import chain
logger = getLogger(__name__)

def get_platform_name():
    from infi.os_info import get_platform_string
    return get_platform_string().split('-')[0]

def _get_platform_specific_storagemodel_class():
    # do platform-specific magic here.
    from .base import StorageModel as PlatformStorageModel  # helps IDEs
    from importlib import import_module
    plat = get_platform_name()
    platform_module_string = "{}.{}".format(__name__, plat)
    platform_module = import_module(platform_module_string)
    try:
        PlatformStorageModel = getattr(platform_module, "{}StorageModel".format(plat.capitalize()))
    except AttributeError:
        msg = "Failed to import platform-specific storage model"
        logger.exception(msg)
        raise chain(ImportError(msg))
    return PlatformStorageModel

def _get_platform_specific_storagemodel():
    return _get_platform_specific_storagemodel_class()()

def get_storage_model():
    """returns a global instance of a `infi.storagemodel.base.StorageModel`. """
    # pylint: disable=W0603,C0103
    global __storage_model
    if __storage_model is None:
        __storage_model = _get_platform_specific_storagemodel()
    return __storage_model
