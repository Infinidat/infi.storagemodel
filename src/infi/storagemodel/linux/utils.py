from infi.storagemodel.base.utils import Utils

class LinuxUtils(Utils):
    def get_free_space(self, path):
        from os import statvfs
        stat_res = statvfs(path)
        return stat_res.f_frsize * stat_res.f_bavail
