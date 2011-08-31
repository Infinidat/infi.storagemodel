
Objects
=======

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

.. module:: infi.storagemodel.base.multipath

Multipath Device
----------------

.. autoclass:: MultipathDevice
    :inherited-members:

Multipath Path
++++++++++++++

.. autoclass:: Path
    :inherited-members:

.. _supported-policies:

Load Balance Policies
+++++++++++++++++++++

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


Connectivity
============

Fiber Channel
-------------

.. module:: infi.storagemodel.connectivity

.. autoclass:: FCConnectivity

