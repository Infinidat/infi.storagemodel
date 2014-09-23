from infi.storagemodel.base.utils import Utils
import ctypes

class WindowsUtils(Utils):
    def get_free_space(self, path):
        free_bytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(path.decode('ascii')), None, None, ctypes.pointer(free_bytes))
        return free_bytes.value
