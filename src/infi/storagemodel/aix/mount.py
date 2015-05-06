"""
TODO no support for mounting yet - this file is a WIP

a good reference: http://www.datadisk.co.uk/html_docs/hp/aix_lvm.htm
rough flow for mounting a scsi/multipath device (in this example hdisk38)

chdev -l hdisk38 -a pv=yes                          # make hdisk38 a physical volume
extendvg rootvg hdisk38                             # add the physical volume to the volume group
mklv -t jfs2 rootvg 1 hdisk38                       # create a logical volume in the volume group with the physical volume
mkfs -V jfs2 /dev/fslv04                            # mkfs. fslv04 is the name of the lv returned from previous command
crfs -v jfs2 -d fslv03 -u fs -m /mnt/arnony -Ayes   # mkfs + add to /etc/filesystems so it will be mountable (-Ayes means persistent mount)
mount /mnt/arnony                                   # mount an FS written in /etc/filesystems
chfs -a size=10G /mnt/arnony                        # capacity doesn't take all available space by default
"""

from ..unix import mount
from infi.pyutils.lazy import cached_method


class AixMountManager(mount.UnixMountManager):
    def _get_file_system_object(self, fsname):
        from .filesystem import AixFileSystem
        return AixFileSystem(fsname)

    @cached_method
    def get_recommended_file_system(self):
        with open("/etc/vfs") as f:
            data = f.read()
        default_lines = [line.split() for line in data.split("\n") if line.startswith("%defaultvfs")]
        if len(default_lines) == 0:
            default_fs = "jfs2"
        else:
            _, default_fs, default_remote_fs = default_lines[0]
        return self._get_file_system_object(default_fs)

    def _get_mount_object(self, entry):
        return AixMount(entry)

class AixMount(mount.UnixMount):
    def __init__(self, mount_entry):
        super(AixMount, self).__init__(mount_entry)
        self._entry = mount_entry

    def get_filesystem(self):
        from .filesystem import AixFileSystem
        return AixFileSystem(self._entry.get_typename())

class AixPersistentMount(AixMount, mount.UnixPersistentMount):
    pass

class AixMountRepository(mount.UnixMountRepository):
    def _get_persistent_mount_object(self, entry):
        return AixPersistentMount(entry)
