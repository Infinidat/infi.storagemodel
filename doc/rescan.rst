
.. _rescan:

Scanning for changes in Storage
===============================

Doing a rescan on the SCSI bus is an expensive operation.

Usually, issuing a rescan on an operating system does not report on comlpetion,
and it takes some time for the upper layers to finish their work.

Since rescan is usually done when there's a change in connectivity or mapping, this moddule
provides an interfaces that blocks until the condition you're expending is True.

The function :py:meth:`.rescan_and_wait_for` accepts a predicate and blocks until the predicate returns True, or timeout is raised.

Let's see some examples.

Examples
--------

.. module:: infi.storagemodel.predicates

Waiting for a new device
++++++++++++++++++++++++

The most common use case is that a volume has been mapped, and you want to wait for it to appear.

For that we have the :class:`.DiskExists` predicate:

.. autoclass:: DiskExists
   :no-members:

Waiting for a new disk is straight-forward:

   >>> from infi.storagemodel import get_storage_model()
   >>> from infi.storagemodel.predicates import DiskExists
   >>> get_storage_model().rescan_and_wait_for(DiskExists("123456"))

This predicate works for both multipath disks and non-multipath disks

Waiting for a device to be gone
+++++++++++++++++++++++++++++++

If you want to rescan after unmapping a volume, use the :class:`DiskNotExists` predicate:

.. autoclass:: DiskNotExists
   :no-members:
 
Fiber Channel mappings
++++++++++++++++++++++

If you performed a connectivity change, you can wait for it to happen.

   >>> from infi.storagemodel.predicates import FiberChannelMappingExists
   >>> predicate = FiberChannelMappingExists("01020304060708", "0a:0b:0c:0d:0e:0f:0g:0h", lun_number=0)
   >>> get_storage_model().rescan_and_wait_for(predicate)

The complete description of the predicates for this use case:

.. autoclass:: FiberChannelMappingExists
   :no-members:

.. autoclass:: FiberChannelMappingNotExists
   :no-members:

The wwn argument can take any WWN format you can think of (lower-case, upper-case, with "-"/":" separators or not).

Waiting for several conditions
++++++++++++++++++++++++++++++

You can also wait for several conditions together:

   >>> from infi.storagemodel.predicates import DiskExists, DiskNotExists, PredicateList
   >>> get_storage_model().rescan_and_wait_for([DiskExists("123"), DiskNotExists("456")])
