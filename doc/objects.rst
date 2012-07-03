
SCSI Objects
============

.. module:: infi.storagemodel.base.scsi

SCSI Device
-----------

.. autoclass:: SCSIDevice
    :inherited-members:

SCSI Block Device
-----------------

.. autoclass:: SCSIBlockDevice
    :show-inheritance:

SCSI Storage Controller Device
------------------------------

.. autoclass:: SCSIStorageController
    :show-inheritance:

Multipath Objects
=================

.. module:: infi.storagemodel.base.multipath

Multipath Device
----------------

.. autoclass:: MultipathDevice
    :inherited-members:

Multipath Path
--------------

.. autoclass:: Path
    :inherited-members:

.. _supported-policies:

Load Balance Policies
---------------------

.. autoclass:: LoadBalancePolicy

.. autoclass:: FailoverOnly
    :show-inheritance:

.. autoclass:: RoundRobin
    :show-inheritance:

.. autoclass:: RoundRobinWithSubset
    :show-inheritance:

.. autoclass:: RoundRobinWithTPGSSubset
    :show-inheritance:

.. autoclass:: RoundRobinWithExplicitSubset
    :show-inheritance:

.. autoclass:: WeightedPaths
    :show-inheritance:

.. autoclass:: LeastBlocks
    :show-inheritance:

.. autoclass:: LeastQueueDepth
    :show-inheritance:

Disk Objects
============
.. module:: infi.storagemodel.base.disk

Disk Drive
----------

.. autoclass:: DiskDrive
    :inherited-members:

Partition Objects
=================

.. module:: infi.storagemodel.base.partition

Partition Table
---------------

.. autoclass:: PartitionTable
    :inherited-members:

Master Boot Record
++++++++++++++++++

.. autoclass:: MBRPartitionTable
    :inherited-members:

GPT
+++

.. autoclass:: GPTPartitionTable
    :inherited-members:

Mount Objects
=============

.. module:: infi.storagemodel.base.mount

Mount
----------

.. autoclass:: Mount
    :inherited-members:

Persistent Mount
++++++++++++++++

.. autoclass:: PersistentMount
    :inherited-members:

File System Objects
===================

.. module:: infi.storagemodel.base.filesystem

Filesystem
----------

.. autoclass:: FileSystem
    :inherited-members:

Filesystem Factory
------------------

.. autoclass:: FileSystemFactoryImpl
    :inherited-members:

Connectivity
============

Fiber Channel
-------------

.. module:: infi.storagemodel.connectivity

.. autoclass:: FCConnectivity


Vendor Information
==================

Infinidat
---------

.. module:: infi.storagemodel.vendor.infinidat.infinibox.mixin

.. autoclass:: InfiniBoxInquiryMixin

.. autoclass:: InfiniBoxVolumeMixin

.. autoclass:: SophisticatedMixin

.. module:: infi.storagemodel.vendor.infinidat.infinibox.naa

.. autoclass:: InfinidatNAA

.. module:: infi.storagemodel.vendor.infinidat.infinibox.fc_port

.. autoclass:: InfinidatFiberChannelPort

