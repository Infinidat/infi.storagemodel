from unittest import TestCase, SkipTest
from mock import Mock, patch
from os import name
from infi.dtypes.hctl import HCTL
from infi.storagemodel.linux.sysfs import Sysfs

class SysfsTestCase(TestCase):
    @patch('os.listdir')
    @patch('__builtin__.open')
    def test_sysfs(self, open_mock, listdir_mock):
        if name == "nt":
            raise SkipTest

        listdir_map = {
            '/sys/class/scsi_device': [ '2:0:0:0', '3:0:0:0', '3:0:1:1', '3:0:1:2', '4:0:0:0', '4:0:1:1', '4:0:1:2',
                                        '5:0:0:0' ],
            # SCSI Disks:
            '/sys/class/scsi_device/2:0:0:0/device/block': [ 'sda' ],
            '/sys/class/scsi_device/2:0:0:0/device/scsi_generic': [ 'sg0' ],
            '/sys/class/scsi_device/3:0:0:0/device/block': [ 'sde' ],
            '/sys/class/scsi_device/3:0:0:0/device/scsi_generic': [ 'sg4' ],
            '/sys/class/scsi_device/3:0:1:1/device/block': [ 'sdf' ],
            '/sys/class/scsi_device/3:0:1:1/device/scsi_generic': [ 'sg2' ],
            '/sys/class/scsi_device/3:0:1:2/device/block': [ 'sdg' ],
            '/sys/class/scsi_device/3:0:1:2/device/scsi_generic': [ 'sg5' ],
            '/sys/class/scsi_device/4:0:0:0/device/block': [ 'sdb' ],
            '/sys/class/scsi_device/4:0:0:0/device/scsi_generic': [ 'sg1' ],
            '/sys/class/scsi_device/4:0:1:1/device/block': [ 'sdc' ],
            '/sys/class/scsi_device/4:0:1:1/device/scsi_generic': [ 'sg7' ],
            '/sys/class/scsi_device/4:0:1:2/device/block': [ 'sdd' ],
            '/sys/class/scsi_device/4:0:1:2/device/scsi_generic': [ 'sg6' ],
            # SCSI Storage Controllers:
            '/sys/class/scsi_device/5:0:0:0/device/scsi_generic': [ 'sg3' ],
        }

        file_map = {
            '/sys/class/scsi_device/2:0:0:0/device/type': '0',
            '/sys/class/scsi_device/2:0:0:0/device/vendor': 'VMware',
            '/sys/class/scsi_device/2:0:0:0/device/block/sda/size': '16777216',
            '/sys/class/scsi_device/2:0:0:0/device/queue_depth': '64',

            '/sys/class/scsi_device/3:0:0:0/device/type': '0',
            '/sys/class/scsi_device/3:0:0:0/device/vendor': 'NFINIDAT',
            '/sys/class/scsi_device/3:0:0:0/device/block/sde/size': '2097156',
            '/sys/class/scsi_device/3:0:0:0/device/queue_depth': '32',

            '/sys/class/scsi_device/3:0:1:1/device/type': '0',
            '/sys/class/scsi_device/3:0:1:1/device/vendor': 'NEXSAN',
            '/sys/class/scsi_device/3:0:1:1/device/block/sdf/size': '1953792',
            '/sys/class/scsi_device/3:0:1:1/device/queue_depth': '32',

            '/sys/class/scsi_device/3:0:1:2/device/type': '0',
            '/sys/class/scsi_device/3:0:1:2/device/vendor': 'NEXSAN',
            '/sys/class/scsi_device/3:0:1:2/device/block/sdg/size': '1953792',
            '/sys/class/scsi_device/3:0:1:2/device/queue_depth': '32',

            '/sys/class/scsi_device/4:0:0:0/device/type': '0',
            '/sys/class/scsi_device/4:0:0:0/device/vendor': 'NFINIDAT',
            '/sys/class/scsi_device/4:0:0:0/device/block/sdb/size': '2097156',
            '/sys/class/scsi_device/4:0:0:0/device/queue_depth': '32',

            '/sys/class/scsi_device/4:0:1:1/device/type': '0',
            '/sys/class/scsi_device/4:0:1:1/device/vendor': 'NEXSAN',
            '/sys/class/scsi_device/4:0:1:1/device/block/sdc/size': '1953792',
            '/sys/class/scsi_device/4:0:1:1/device/queue_depth': '32',

            '/sys/class/scsi_device/4:0:1:2/device/type': '0',
            '/sys/class/scsi_device/4:0:1:2/device/vendor': 'NEXSAN',
            '/sys/class/scsi_device/4:0:1:2/device/block/sdd/size': '1953792',
            '/sys/class/scsi_device/4:0:1:2/device/queue_depth': '32',

            '/sys/class/scsi_device/5:0:0:0/device/type': '12',
            '/sys/class/scsi_device/5:0:0:0/device/vendor': 'NFINIDAT',
            '/sys/class/scsi_device/5:0:0:0/device/queue_depth': '32',
        }

        def create_file_context_manager(path, mode):
            file_mock = Mock()
            file_mock.read = Mock(return_value=file_map[path])
            cm = Mock()
            cm.__enter__ = Mock(return_value=file_mock)
            cm.__exit__ = Mock()
            return cm

        disk_properties = {
            'sda': dict(queue_depth=64, sysfs_size=16777216, hctl='2:0:0:0', vendor='VMware'),
            'sde': dict(queue_depth=32, sysfs_size=2097156, hctl='3:0:0:0', vendor='NFINIDAT'),
            'sdf': dict(queue_depth=32, sysfs_size=1953792, hctl='3:0:1:1', vendor='NEXSAN'),
            'sdg': dict(queue_depth=32, sysfs_size=1953792, hctl='3:0:1:2', vendor='NEXSAN'),
            'sdb': dict(queue_depth=32, sysfs_size=2097156, hctl='4:0:0:0', vendor='NFINIDAT'),
            'sdc': dict(queue_depth=32, sysfs_size=1953792, hctl='4:0:1:1', vendor='NEXSAN'),
            'sdd': dict(queue_depth=32, sysfs_size=1953792, hctl='4:0:1:2', vendor='NEXSAN'),
        }

        listdir_mock.side_effect = listdir_map.get
        open_mock.side_effect = create_file_context_manager

        sysfs = Sysfs()

        disks = sysfs.get_all_scsi_disks()
        self.assertEquals(7, len(disks))

        for disk in disks:
            block_dev = disk.get_block_device_name()
            self.assertTrue(block_dev in disk_properties)

            self.assertEquals(HCTL.from_string(disk_properties[block_dev]['hctl']), disk.get_hctl())
            self.assertEquals(disk_properties[block_dev]['queue_depth'], disk.get_queue_depth())
            self.assertEquals(disk_properties[block_dev]['sysfs_size'] * 512, disk.get_size_in_bytes())
            self.assertEquals(disk_properties[block_dev]['vendor'], disk.get_vendor())
