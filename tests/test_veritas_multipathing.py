from infi.storagemodel.linux.scsi import LinuxSCSIBlockDevice
from infi.dtypes.hctl import HCTL
from infi.storagemodel import get_storage_model
from infi.pyutils.contexts import contextmanager
from infi.pyutils.lazy import clear_cache
from unittest import TestCase, SkipTest
from mock import Mock, patch
from os import name
from infi.os_info import get_platform_string

VXDMPADM_OUTPUT_TEMPLATE = """dmpdev      = sda
state       = disabled
enclosure   = other_disks
cab-sno     = OTHER_DISKS
asl     = otherdisks
vid     = VMware
pid     = Virtual disk
array-name  = OTHER_DISKS
array-type  = OTHER_DISKS
iopolicy    = Balanced
avid        = -
lun-sno     =
udid        = VMware%5FVirtual%20disk%5FOTHER%5FDISKS%5Fhost-ci102.lab.il.infinidat.com%5F%2Fdev%2Fsda
dev-attr    = -
lun_type    = -
scsi3_vpd   = -
replicated  = no
num_paths   = 1
###path     = name state type transport ctlr hwpath aportID aportWWN attr
path        = sda disabled(a) - SCSI c0 c0 - - -

dmpdev      = infinibox0_0ace
state       = enabled
enclosure   = infinibox0
cab-sno     = 4e4f
asl     = libvxinfinibox.so
vid     = {vid}
pid     = {pid}
array-name  = InfiniBox
array-type  = A/A
iopolicy    = MinimumQ
avid        = 0ace
lun-sno     = 742b0f000004e4f0000000000000ace
udid        = NFINIDAT%5FInfiniBox%5F4e4f%5F742b0f000004e4f0000000000000ace
dev-attr    = tprclm
lun_type    = std
scsi3_vpd   = NAA:6742B0F000004E4F0000000000000ACE
replicated  = no
num_paths   = 6
###path     = name state type transport ctlr hwpath aportID aportWWN attr
{paths}
"""

SIX_PATHS = """path        = sdc enabled(a) - FC c3 c3 2-2 57:42:b0:f0:00:4e:4f:32 -
path        = sdn enabled(a) - FC c3 c3 2-2 57:42:b0:f0:00:4e:4f:22 -
path        = sdbf enabled(a) - FC c3 c3 1-1 57:42:b0:f0:00:4e:4f:11 -
path        = sdau enabled(a) - FC c3 c3 1-1 57:42:b0:f0:00:4e:4f:21 -
path        = sdy enabled(a) - FC c3 c3 2-2 57:42:b0:f0:00:4e:4f:12 -
path        = sdaj enabled(a) - FC c3 c3 1-1 57:42:b0:f0:00:4e:4f:31 -
"""

ALL_DISABLED = """path        = sdc disabled(a) - FC c3 c3 2-2 57:42:b0:f0:00:4e:4f:32 -
path        = sdn disabled(a) - FC c3 c3 2-2 57:42:b0:f0:00:4e:4f:22 -
path        = sdbf disabled(a) - FC c3 c3 1-1 57:42:b0:f0:00:4e:4f:11 -
path        = sdau disabled(a) - FC c3 c3 1-1 57:42:b0:f0:00:4e:4f:21 -
path        = sdy disabled(a) - FC c3 c3 2-2 57:42:b0:f0:00:4e:4f:12 -
path        = sdaj disabled(a) - FC c3 c3 1-1 57:42:b0:f0:00:4e:4f:31 -
"""

ONE_ENABLED = """path        = sdc disabled(a) - FC c3 c3 2-2 57:42:b0:f0:00:4e:4f:32 -
path        = sdn disabled(a) - FC c3 c3 2-2 57:42:b0:f0:00:4e:4f:22 -
path        = sdbf disabled(a) - FC c3 c3 1-1 57:42:b0:f0:00:4e:4f:11 -
path        = sdau disabled(a) - FC c3 c3 1-1 57:42:b0:f0:00:4e:4f:21 -
path        = sdy enabled(a) - FC c3 c3 2-2 57:42:b0:f0:00:4e:4f:12 -
path        = sdaj disabled(a) - FC c3 c3 1-1 57:42:b0:f0:00:4e:4f:31 -
"""


OTHER_VENDOR_OUTPUT = """dmpdev     = sdb
state       = enabled
enclosure   = InfiniBox0
cab-sno     = 0422
asl     = libvxinfinibox.so
vid     = NFINIDAT
pid     = InfiniBox
array-name  = InfiniBox
array-type  = A/A
iopolicy    = MinimumQ
avid        = 761d
lun-sno     = 742b0f000000422000000000000761d
udid        = NFINIDAT%5FInfiniBox%5F0422%5F742b0f000000422000000000000761d
dev-attr    = tprclm
lun_type    = std
scsi3_vpd   = NAA:6742B0F000000422000000000000761D
replicated  = no
num_paths   = 6
###path     = name state type transport ctlr hwpath aportID aportWWN attr
path        = sdw enabled(a) - FC c9 c9 6-6 57:42:b0:f0:00:04:22:26 -
path        = sdak enabled(a) - FC c9 c9 6-6 57:42:b0:f0:00:04:22:16 -
path        = sdad enabled(a) - FC c9 c9 6-6 57:42:b0:f0:00:04:22:36 -
path        = sdp enabled(a) - FC c8 c8 2-2 57:42:b0:f0:00:04:22:12 -
path        = sdi enabled(a) - FC c8 c8 2-2 57:42:b0:f0:00:04:22:32 -
path        = sdb enabled(a) - FC c8 c8 2-2 57:42:b0:f0:00:04:22:22 -

dmpdev      = sdc
state       = enabled
enclosure   = InfiniBox0
cab-sno     = 0422
asl     = libvxinfinibox.so
vid     = NFINIDAT
pid     = InfiniBox
array-name  = InfiniBox
array-type  = A/A
iopolicy    = MinimumQ
avid        = 7624
lun-sno     = 742b0f0000004220000000000007624
udid        = NFINIDAT%5FInfiniBox%5F0422%5F742b0f0000004220000000000007624
dev-attr    = tprclm
lun_type    = std
scsi3_vpd   = NAA:6742B0F0000004220000000000007624
replicated  = no
num_paths   = 6
###path     = name state type transport ctlr hwpath aportID aportWWN attr
path        = sdx enabled(a) - FC c9 c9 6-6 57:42:b0:f0:00:04:22:26 -
path        = sdal enabled(a) - FC c9 c9 6-6 57:42:b0:f0:00:04:22:16 -
path        = sdae enabled(a) - FC c9 c9 6-6 57:42:b0:f0:00:04:22:36 -
path        = sdq enabled(a) - FC c8 c8 2-2 57:42:b0:f0:00:04:22:12 -
path        = sdj enabled(a) - FC c8 c8 2-2 57:42:b0:f0:00:04:22:32 -
path        = sdc enabled(a) - FC c8 c8 2-2 57:42:b0:f0:00:04:22:22 -

dmpdev      = sdd
state       = enabled
enclosure   = InfiniBox0
cab-sno     = 0422
asl     = libvxinfinibox.so
vid     = NFINIDAT
pid     = InfiniBox
array-name  = InfiniBox
array-type  = A/A
iopolicy    = MinimumQ
avid        = 7625
lun-sno     = 742b0f0000004220000000000007625
udid        = NFINIDAT%5FInfiniBox%5F0422%5F742b0f0000004220000000000007625
dev-attr    = tprclm
lun_type    = std
scsi3_vpd   = NAA:6742B0F0000004220000000000007625
replicated  = no
num_paths   = 6
###path     = name state type transport ctlr hwpath aportID aportWWN attr
path        = sdam enabled(a) - FC c9 c9 6-6 57:42:b0:f0:00:04:22:16 -
path        = sdy enabled(a) - FC c9 c9 6-6 57:42:b0:f0:00:04:22:26 -
path        = sdaf enabled(a) - FC c9 c9 6-6 57:42:b0:f0:00:04:22:36 -
path        = sdr enabled(a) - FC c8 c8 2-2 57:42:b0:f0:00:04:22:12 -
path        = sdd enabled(a) - FC c8 c8 2-2 57:42:b0:f0:00:04:22:22 -
path        = sdk enabled(a) - FC c8 c8 2-2 57:42:b0:f0:00:04:22:32 -

dmpdev      = sde
state       = enabled
enclosure   = InfiniBox0
cab-sno     = 0422
asl     = libvxinfinibox.so
vid     = NFINIDAT
pid     = InfiniBox
array-name  = InfiniBox
array-type  = A/A
iopolicy    = MinimumQ
avid        = 7626
lun-sno     = 742b0f0000004220000000000007626
udid        = NFINIDAT%5FInfiniBox%5F0422%5F742b0f0000004220000000000007626
dev-attr    = tprclm
lun_type    = std
scsi3_vpd   = NAA:6742B0F0000004220000000000007626
replicated  = no
num_paths   = 6
###path     = name state type transport ctlr hwpath aportID aportWWN attr
path        = sdan enabled(a) - FC c9 c9 6-6 57:42:b0:f0:00:04:22:16 -
path        = sdz enabled(a) - FC c9 c9 6-6 57:42:b0:f0:00:04:22:26 -
path        = sdag enabled(a) - FC c9 c9 6-6 57:42:b0:f0:00:04:22:36 -
path        = sdl enabled(a) - FC c8 c8 2-2 57:42:b0:f0:00:04:22:32 -
path        = sde enabled(a) - FC c8 c8 2-2 57:42:b0:f0:00:04:22:22 -
path        = sds enabled(a) - FC c8 c8 2-2 57:42:b0:f0:00:04:22:12 -

dmpdev      = sdf
state       = enabled
enclosure   = InfiniBox0
cab-sno     = 0422
asl     = libvxinfinibox.so
vid     = NFINIDAT
pid     = InfiniBox
array-name  = InfiniBox
array-type  = A/A
iopolicy    = MinimumQ
avid        = 7627
lun-sno     = 742b0f0000004220000000000007627
udid        = NFINIDAT%5FInfiniBox%5F0422%5F742b0f0000004220000000000007627
dev-attr    = tprclm
lun_type    = std
scsi3_vpd   = NAA:6742B0F0000004220000000000007627
replicated  = no
num_paths   = 6
###path     = name state type transport ctlr hwpath aportID aportWWN attr
path        = sdao enabled(a) - FC c9 c9 6-6 57:42:b0:f0:00:04:22:16 -
path        = sdaa enabled(a) - FC c9 c9 6-6 57:42:b0:f0:00:04:22:26 -
path        = sdah enabled(a) - FC c9 c9 6-6 57:42:b0:f0:00:04:22:36 -
path        = sdf enabled(a) - FC c8 c8 2-2 57:42:b0:f0:00:04:22:22 -
path        = sdm enabled(a) - FC c8 c8 2-2 57:42:b0:f0:00:04:22:32 -
path        = sdt enabled(a) - FC c8 c8 2-2 57:42:b0:f0:00:04:22:12 -

dmpdev      = sdg
state       = enabled
enclosure   = InfiniBox0
cab-sno     = 0422
asl     = libvxinfinibox.so
vid     = NFINIDAT
pid     = InfiniBox
array-name  = InfiniBox
array-type  = A/A
iopolicy    = MinimumQ
avid        = 7628
lun-sno     = 742b0f0000004220000000000007628
udid        = NFINIDAT%5FInfiniBox%5F0422%5F742b0f0000004220000000000007628
dev-attr    = tprclm
lun_type    = std
scsi3_vpd   = NAA:6742B0F0000004220000000000007628
replicated  = no
num_paths   = 6
###path     = name state type transport ctlr hwpath aportID aportWWN attr
path        = sdai enabled(a) - FC c9 c9 6-6 57:42:b0:f0:00:04:22:36 -
path        = sdab enabled(a) - FC c9 c9 6-6 57:42:b0:f0:00:04:22:26 -
path        = sdap enabled(a) - FC c9 c9 6-6 57:42:b0:f0:00:04:22:16 -
path        = sdu enabled(a) - FC c8 c8 2-2 57:42:b0:f0:00:04:22:12 -
path        = sdg enabled(a) - FC c8 c8 2-2 57:42:b0:f0:00:04:22:22 -
path        = sdn enabled(a) - FC c8 c8 2-2 57:42:b0:f0:00:04:22:32 -

dmpdev      = sdh
state       = enabled
enclosure   = InfiniBox0
cab-sno     = 0422
asl     = libvxinfinibox.so
vid     = NFINIDAT
pid     = InfiniBox
array-name  = InfiniBox
array-type  = A/A
iopolicy    = MinimumQ
avid        = 7629
lun-sno     = 742b0f0000004220000000000007629
udid        = NFINIDAT%5FInfiniBox%5F0422%5F742b0f0000004220000000000007629
dev-attr    = tprclm
lun_type    = std
scsi3_vpd   = NAA:6742B0F0000004220000000000007629
replicated  = no
num_paths   = 6
###path     = name state type transport ctlr hwpath aportID aportWWN attr
path        = sdac enabled(a) - FC c9 c9 6-6 57:42:b0:f0:00:04:22:26 -
path        = sdaq enabled(a) - FC c9 c9 6-6 57:42:b0:f0:00:04:22:16 -
path        = sdaj enabled(a) - FC c9 c9 6-6 57:42:b0:f0:00:04:22:36 -
path        = sdv enabled(a) - FC c8 c8 2-2 57:42:b0:f0:00:04:22:12 -
path        = sdo enabled(a) - FC c8 c8 2-2 57:42:b0:f0:00:04:22:32 -
path        = sdh enabled(a) - FC c8 c8 2-2 57:42:b0:f0:00:04:22:22 -

dmpdev      = sdar
state       = enabled
enclosure   = XIV0
cab-sno     = 780312397
asl     = libvxxiv.so
vid     = IBM
pid     = 2810XIV
array-name  = XIV
array-type  = ALUA
iopolicy    = MinimumQ
avid        = 12528
lun-sno     = 30F0
udid        = IBM%5F2810XIV%5F306D%5F30F0
dev-attr    = tprclm RAID_10
lun_type    = std
scsi3_vpd   = EUI:00173800306D30F0
raid_type   = RAID_10
replicated  = no
num_paths   = 2
###path     = name state type transport ctlr hwpath aportID aportWWN attr
path        = sdar enabled(a) primary FC c9 c9 0-400 50:01:73:80:30:6d:01:40 -
path        = sdaz enabled(a) primary FC c8 c8 0-500 50:01:73:80:30:6d:01:50 -

dmpdev      = sdas
state       = enabled
enclosure   = XIV0
cab-sno     = 780312397
asl     = libvxxiv.so
vid     = IBM
pid     = 2810XIV
array-name  = XIV
array-type  = ALUA
iopolicy    = MinimumQ
avid        = 12529
lun-sno     = 30F1
udid        = IBM%5F2810XIV%5F306D%5F30F1
dev-attr    = tprclm RAID_10
lun_type    = std
scsi3_vpd   = EUI:00173800306D30F1
raid_type   = RAID_10
replicated  = no
num_paths   = 2
###path     = name state type transport ctlr hwpath aportID aportWWN attr
path        = sdas enabled(a) primary FC c9 c9 0-400 50:01:73:80:30:6d:01:40 -
path        = sdba enabled(a) primary FC c8 c8 0-500 50:01:73:80:30:6d:01:50 -

dmpdev      = sdat
state       = enabled
enclosure   = XIV0
cab-sno     = 780312397
asl     = libvxxiv.so
vid     = IBM
pid     = 2810XIV
array-name  = XIV
array-type  = ALUA
iopolicy    = MinimumQ
avid        = 12530
lun-sno     = 30F2
udid        = IBM%5F2810XIV%5F306D%5F30F2
dev-attr    = tprclm RAID_10
lun_type    = std
scsi3_vpd   = EUI:00173800306D30F2
raid_type   = RAID_10
replicated  = no
num_paths   = 2
###path     = name state type transport ctlr hwpath aportID aportWWN attr
path        = sdat enabled(a) primary FC c9 c9 0-400 50:01:73:80:30:6d:01:40 -
path        = sdbb enabled(a) primary FC c8 c8 0-500 50:01:73:80:30:6d:01:50 -

dmpdev      = sdau
state       = enabled
enclosure   = XIV0
cab-sno     = 780312397
asl     = libvxxiv.so
vid     = IBM
pid     = 2810XIV
array-name  = XIV
array-type  = ALUA
iopolicy    = MinimumQ
avid        = 12531
lun-sno     = 30F3
udid        = IBM%5F2810XIV%5F306D%5F30F3
dev-attr    = tprclm RAID_10
lun_type    = std
scsi3_vpd   = EUI:00173800306D30F3
raid_type   = RAID_10
replicated  = no
num_paths   = 2
###path     = name state type transport ctlr hwpath aportID aportWWN attr
path        = sdau enabled(a) primary FC c9 c9 0-400 50:01:73:80:30:6d:01:40 -
path        = sdbc enabled(a) primary FC c8 c8 0-500 50:01:73:80:30:6d:01:50 -

dmpdev      = sdav
state       = enabled
enclosure   = XIV0
cab-sno     = 780312397
asl     = libvxxiv.so
vid     = IBM
pid     = 2810XIV
array-name  = XIV
array-type  = ALUA
iopolicy    = MinimumQ
avid        = 12532
lun-sno     = 30F4
udid        = IBM%5F2810XIV%5F306D%5F30F4
dev-attr    = tprclm RAID_10
lun_type    = std
scsi3_vpd   = EUI:00173800306D30F4
raid_type   = RAID_10
replicated  = no
num_paths   = 2
###path     = name state type transport ctlr hwpath aportID aportWWN attr
path        = sdav enabled(a) primary FC c9 c9 0-400 50:01:73:80:30:6d:01:40 -
path        = sdbd enabled(a) primary FC c8 c8 0-500 50:01:73:80:30:6d:01:50 -

dmpdev      = sdaw
state       = enabled
enclosure   = XIV0
cab-sno     = 780312397
asl     = libvxxiv.so
vid     = IBM
pid     = 2810XIV
array-name  = XIV
array-type  = ALUA
iopolicy    = MinimumQ
avid        = 12533
lun-sno     = 30F5
udid        = IBM%5F2810XIV%5F306D%5F30F5
dev-attr    = tprclm RAID_10
lun_type    = std
scsi3_vpd   = EUI:00173800306D30F5
raid_type   = RAID_10
replicated  = no
num_paths   = 2
###path     = name state type transport ctlr hwpath aportID aportWWN attr
path        = sdaw enabled(a) primary FC c9 c9 0-400 50:01:73:80:30:6d:01:40 -
path        = sdbe enabled(a) primary FC c8 c8 0-500 50:01:73:80:30:6d:01:50 -

dmpdev      = sdax
state       = enabled
enclosure   = XIV0
cab-sno     = 780312397
asl     = libvxxiv.so
vid     = IBM
pid     = 2810XIV
array-name  = XIV
array-type  = ALUA
iopolicy    = MinimumQ
avid        = 12534
lun-sno     = 30F6
udid        = IBM%5F2810XIV%5F306D%5F30F6
dev-attr    = tprclm RAID_10
lun_type    = std
scsi3_vpd   = EUI:00173800306D30F6
raid_type   = RAID_10
replicated  = no
num_paths   = 2
###path     = name state type transport ctlr hwpath aportID aportWWN attr
path        = sdax enabled(a) primary FC c9 c9 0-400 50:01:73:80:30:6d:01:40 -
path        = sdbf enabled(a) primary FC c8 c8 0-500 50:01:73:80:30:6d:01:50 -

dmpdev      = sday
state       = enabled
enclosure   = XIV0
cab-sno     = 780312397
asl     = libvxxiv.so
vid     = IBM
pid     = 2810XIV
array-name  = XIV
array-type  = ALUA
iopolicy    = MinimumQ
avid        = 12535
lun-sno     = 30F7
udid        = IBM%5F2810XIV%5F306D%5F30F7
dev-attr    = tprclm RAID_10
lun_type    = std
scsi3_vpd   = EUI:00173800306D30F7
raid_type   = RAID_10
replicated  = no
num_paths   = 2
###path     = name state type transport ctlr hwpath aportID aportWWN attr
path        = sday enabled(a) primary FC c9 c9 0-400 50:01:73:80:30:6d:01:40 -
path        = sdbg enabled(a) primary FC c8 c8 0-500 50:01:73:80:30:6d:01:50 -

dmpdev      = sdbh
state       = enabled
enclosure   = XIV0
cab-sno     = 780312397
asl     = libvxxiv.so
vid     = IBM
pid     = 2810XIV
array-name  = XIV
array-type  = ALUA
iopolicy    = MinimumQ
avid        = 9881
lun-sno     = 2699
udid        = IBM%5F2810XIV%5F306D%5F2699
dev-attr    = tprclm RAID_10
lun_type    = std
scsi3_vpd   = EUI:00173800306D2699
raid_type   = RAID_10
replicated  = no
num_paths   = 2
###path     = name state type transport ctlr hwpath aportID aportWWN attr
path        = sdbi enabled(a) primary FC c9 c9 0-400 50:01:73:80:30:6d:01:40 -
path        = sdbh enabled(a) primary FC c8 c8 0-500 50:01:73:80:30:6d:01:50 -
"""


STORAGEMODEL_360_VERITAS_OUTPUT = """dmpdev        = disk_0
state       = enabled
enclosure   = disk
cab-sno     = DISKS
asl     = scsi3_jbod
vid     = HITACHI
pid     = H109060SESUN600G
array-name  = Disk
array-type  = Disk
iopolicy    = MinimumQ
avid        = -
lun-sno     = 5000CCA0561FA034
udid        = HITACHI%5FH109060SESUN600G%5FDISKS%5F5000CCA0561FA034
dev-attr    = -
###path     = name state type transport ctlr hwpath aportID aportWWN attr
path        = c0t5000CCA0561FA034d0s2 enabled(a) - FC c0 /scsi_vhci - - -

dmpdev      = disk_1
state       = enabled
enclosure   = disk
cab-sno     = DISKS
asl     = scsi3_jbod
vid     = HITACHI
pid     = H109060SESUN600G
array-name  = Disk
array-type  = Disk
iopolicy    = MinimumQ
avid        = -
lun-sno     = 5000CCA056241EE8
udid        = HITACHI%5FH109060SESUN600G%5FDISKS%5F5000CCA056241EE8
dev-attr    = -
###path     = name state type transport ctlr hwpath aportID aportWWN attr
path        = c0t5000CCA056241EE8d0s2 enabled(a) - FC c0 /scsi_vhci - - -

dmpdev      = disk_2
state       = enabled
enclosure   = disk
cab-sno     = DISKS
asl     = scsi3_jbod
vid     = HITACHI
pid     = H109060SESUN600G
array-name  = Disk
array-type  = Disk
iopolicy    = MinimumQ
avid        = -
lun-sno     = 5000CCA0562421AC
udid        = HITACHI%5FH109060SESUN600G%5FDISKS%5F5000CCA0562421AC
dev-attr    = -
###path     = name state type transport ctlr hwpath aportID aportWWN attr
path        = c0t5000CCA0562421ACd0s2 enabled(a) - FC c0 /scsi_vhci - - -

dmpdev      = disk_3
state       = enabled
enclosure   = disk
cab-sno     = DISKS
asl     = scsi3_jbod
vid     = HITACHI
pid     = H109060SESUN600G
array-name  = Disk
array-type  = Disk
iopolicy    = MinimumQ
avid        = -
lun-sno     = 5000CCA056242200
udid        = HITACHI%5FH109060SESUN600G%5FDISKS%5F5000CCA056242200
dev-attr    = -
###path     = name state type transport ctlr hwpath aportID aportWWN attr
path        = c0t5000CCA056242200d0s2 enabled(a) - FC c0 /scsi_vhci - - -

dmpdev      = aluadisk0_0
state       = enabled
enclosure   = aluadisk0
cab-sno     = ALUAdisk
asl     = scsi3_jbod
vid     = NFINIDA
pid     = InfiniBox
array-name  = aluadisk
array-type  = ALUA
iopolicy    = MinimumQ
avid        = -
lun-sno     = 6742B0F0000004AA0000000000001B1B
udid        = NFINIDAT%5FInfiniBox%5FALUAdisk%5F6742B0F0000004AA0000000000001B1B
dev-attr    = -
###path     = name state type transport ctlr hwpath aportID aportWWN attr
path        = c0t6742B0F0000004AA0000000000001B1Bd0s2 enabled(a) primary FC c0 /scsi_vhci - 57:42:b0:f0:00:04:aa:11 -
"""

HPT_2110_VERITAS_OUTPUT = '''dmpdev       = sda
state       = enabled
enclosure   = other_disks
cab-sno     = OTHER_DISKS
asl     = otherdisks
vid     = VMware
pid     = Virtual disk
array-name  = OTHER_DISKS
array-type  = OTHER_DISKS
iopolicy    = Balanced
avid        = -
lun-sno     =
udid        = VMware%5FVirtual%20disk%5FOTHER%5FDISKS%5Fhost-ci097.lab.il.infinidat.com%5F%2Fdev%2Fsda
dev-attr    = -
lun_type    = -
scsi3_vpd   = -
replicated  = no
num_paths   = 1
###path     = name state type transport ctlr hwpath aportID aportWWN attr
path        = sda enabled(a) - SCSI c0 c0 - - -

dmpdev      = infinibox0_4d0a
state       = enabled
enclosure   = infinibox0
cab-sno     = 7555
asl     = libvxinfinibox.so
vid     = NFINIDAT
pid     = InfiniBox
array-name  = InfiniBox
array-type  = A/A
iopolicy    = MinimumQ
avid        = 4d0a
lun-sno     = 742b0f0000075550000000000004d0a
udid        = NFINIDAT%5FInfiniBox%5F7555%5F742b0f0000075550000000000004d0a
dev-attr    = tprclm
lun_type    = std
scsi3_vpd   = NAA:6742B0F0000075550000000000004D0A
replicated  = no
num_paths   = 1
###path     = name state type transport ctlr hwpath aportID aportWWN attr
path        = sdb enabled(a) - FC c3 c3 1-1 - -
'''
class MockSCSIBlockDevice(LinuxSCSIBlockDevice):
    def get_hctl(self):
        return HCTL(1,2,3,4)


@contextmanager
def veritas_multipathing_context(output):
    if "windows" in get_platform_string():
        raise SkipTest

    with patch('infi.storagemodel.unix.veritas_multipath.VeritasMultipathClient.read_paths_list') as read_paths_list:
        with patch('infi.storagemodel.linux.sysfs.Sysfs.find_scsi_disk_by_hctl') as find_scsi_disk_by_hctl:
            with patch('infi.storagemodel.base.scsi.SCSIModel.find_scsi_block_device_by_block_access_path') as find_func:
                with patch('infi.storagemodel.linux.scsi.is_sg_module_loaded') as is_sg_module_loaded:
                        with patch("infi.storagemodel.get_storage_model") as get_storage_model:
                            from infi.storagemodel.linux import LinuxStorageModel
                            find_func.return_value = MockSCSIBlockDevice(None)
                            find_scsi_disk_by_hctl.return_value = None
                            read_paths_list.return_value = output
                            is_sg_module_loaded.return_value = True
                            sm = LinuxStorageModel()
                            get_storage_model.return_value = sm
                            yield sm.get_veritas_multipath()


class VeritasMultipathingTestCase(TestCase):
    def test_vxdmpadm_output(self):
        vxdmpadm_output = VXDMPADM_OUTPUT_TEMPLATE.format(paths=SIX_PATHS, vid="NFINIDAT", pid="InfiniBox")
        with veritas_multipathing_context(vxdmpadm_output) as veritas_multipath:
            block_devices = veritas_multipath.get_all_multipath_block_devices()
            self.assertEqual(len(block_devices), 1)
            self.assertEqual(len(block_devices[0].get_paths()), 6)

    def test_vxdmpadm_output_no_paths(self):
        vxdmpadm_output = VXDMPADM_OUTPUT_TEMPLATE.format(paths="", vid="NFINIDAT", pid="InfiniBox")
        with veritas_multipathing_context(vxdmpadm_output) as veritas_multipath:
            block_devices = veritas_multipath.get_all_multipath_block_devices()
            self.assertEqual(len(block_devices), 0)

    def test_vxdmpadm_output_all_paths_disabled(self):
        vxdmpadm_output = VXDMPADM_OUTPUT_TEMPLATE.format(paths=ALL_DISABLED, vid="NFINIDAT", pid="InfiniBox")
        with veritas_multipathing_context(vxdmpadm_output) as veritas_multipath:
            block_devices = veritas_multipath.get_all_multipath_block_devices()
            self.assertEqual(len(block_devices), 0)

    def test_vxdmpadm_output_one_path_enabled(self):
        vxdmpadm_output = VXDMPADM_OUTPUT_TEMPLATE.format(paths=ONE_ENABLED, vid="NFINIDAT", pid="InfiniBox")
        with veritas_multipathing_context(vxdmpadm_output) as veritas_multipath:
            block_devices = veritas_multipath.get_all_multipath_block_devices()
            self.assertEqual(len(block_devices), 1)
            self.assertEqual(len(block_devices[0].get_paths()), 6)
            self.assertEqual(len([p for p in block_devices[0].get_paths() if p.get_state() == "up"]), 1)

    @patch('infi.storagemodel.base.inquiry.InquiryInformationMixin.get_scsi_vendor_id_or_unknown_on_error')
    def test_vxdmpadm_output_bad_vid(self, get_scsi_vendor_id_or_unknown_on_error):
        from infi.storagemodel.vendor.infinidat.shortcuts import get_infinidat_veritas_multipath_block_devices
        vid, pid = ("NFINIDAS", "InfiniBox")
        vxdmpadm_output = VXDMPADM_OUTPUT_TEMPLATE.format(paths=SIX_PATHS, vid=vid, pid=pid)
        get_scsi_vendor_id_or_unknown_on_error.return_value = vid, pid
        with veritas_multipathing_context(vxdmpadm_output) as veritas_multipath:
            block_devices = get_infinidat_veritas_multipath_block_devices()
            self.assertEqual(len(block_devices), 0)

    @patch('infi.storagemodel.base.inquiry.InquiryInformationMixin.get_scsi_vendor_id_or_unknown_on_error')
    def test_vxdmpadm_output_bad_pid(self, get_scsi_vendor_id_or_unknown_on_error):
        from infi.storagemodel.vendor.infinidat.shortcuts import get_infinidat_veritas_multipath_block_devices
        vid, pid = ("NFINIDAT", "InfiniBos")
        vxdmpadm_output = VXDMPADM_OUTPUT_TEMPLATE.format(paths=SIX_PATHS, vid=vid, pid=pid)
        get_scsi_vendor_id_or_unknown_on_error.return_value = (vid, pid)
        with veritas_multipathing_context(vxdmpadm_output) as veritas_multipath:
            block_devices = get_infinidat_veritas_multipath_block_devices()
            self.assertEqual(len(block_devices), 0)

    def test_vxdmpadm_output_other_vendor(self):
        vxdmpadm_output = OTHER_VENDOR_OUTPUT
        with veritas_multipathing_context(vxdmpadm_output) as veritas_multipath:
            block_devices = veritas_multipath.get_all_multipath_block_devices()
            self.assertEqual(len(block_devices), 16)
            self.assertEqual(len(block_devices[0].get_paths()), 6)
            self.assertEqual(len(block_devices[-1].get_paths()), 2)

    def test_storagemodel_360_output(self):
        vxdmpadm_output = STORAGEMODEL_360_VERITAS_OUTPUT
        with veritas_multipathing_context(vxdmpadm_output) as veritas_multipath:
            block_devices = veritas_multipath.get_all_multipath_block_devices()
            # there are 5 devices in the output but only one is multipathed
            self.assertEqual(len(block_devices), 5)

    def test_hpt_2110_output(self):
        vxdmpadm_output = HPT_2110_VERITAS_OUTPUT
        with veritas_multipathing_context(vxdmpadm_output) as veritas_multipath:
            block_devices = veritas_multipath.get_all_multipath_block_devices()
            self.assertEqual(len(block_devices), 2)
            self.assertEqual(len(block_devices[-1].get_paths()), 1)
