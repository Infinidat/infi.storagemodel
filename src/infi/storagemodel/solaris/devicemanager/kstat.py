import sys
import ctypes
from infi.pyutils.lazy import cached_method
from infi.os_info import get_platform_string
from infi.pyutils.contexts import contextmanager
from infi.storagemodel.base.multipath import PathStatistics
from infi.cwrap import WrappedFunction, errcheck_nothing, IN, IN_OUT
from infi.storagemodel.solaris.devicemanager import DeviceManager

from logging import getLogger
logger = getLogger(__name__)

KSTAT_STRLEN = 31

KSTAT_TYPE_RAW       =  0
KSTAT_TYPE_NAMED     =  1
KSTAT_TYPE_INTR      =  2
KSTAT_TYPE_IO        =  3
KSTAT_TYPE_TIMER     =  4
KSTAT_NUM_TYPES      =  5

c_kid_t = ctypes.c_int
c_kstat_string = ctypes.c_char * KSTAT_STRLEN
c_hrtime_t = ctypes.c_longlong

class kstat_t(ctypes.Structure):
    pass
kstat_t_p = ctypes.POINTER(kstat_t)
kstat_t._fields_ = [
        ('ks_crtime', c_hrtime_t),
        ('ks_next', kstat_t_p),
        ('ks_kid', c_kid_t),
        ('ks_module', c_kstat_string),
        ('ks_resv', ctypes.c_ubyte),
        ('ks_instance', ctypes.c_int),
        ('ks_name', c_kstat_string),
        ('ks_type', ctypes.c_ubyte),
        ('ks_class', c_kstat_string),
        ('ks_flags', ctypes.c_ubyte),
        ('ks_data', ctypes.c_void_p),
        ('ks_ndata', ctypes.c_uint),
        ('ks_data_size', ctypes.c_size_t),
        ('ks_snaptime', c_hrtime_t),
        ('ks_update', ctypes.c_void_p),
        ('ks_private', ctypes.c_void_p),
        ('ks_snapshot', ctypes.c_void_p),
        ('ks_lock', ctypes.c_void_p)
]

class kstat_ctl_t(ctypes.Structure):
    _fields_ = [
        ('kc_chain_id', c_kid_t),
        ('kc_chain', kstat_t_p),
        ('kc_kd', ctypes.c_int)
    ]
kstat_ctl_t_p = ctypes.POINTER(kstat_ctl_t)

class kstat_io_t(ctypes.Structure):
    _fields_ = [
        ('nread',ctypes.c_ulonglong),
        ('nwritten', ctypes.c_ulonglong),
        ('reads',ctypes.c_uint),
        ('writes',ctypes.c_uint),
        ('wtime',c_hrtime_t),
        ('wlentime',c_hrtime_t),
        ('wlastupdate',c_hrtime_t),
        ('rtime',c_hrtime_t),
        ('rlentime',c_hrtime_t),
        ('rlastupdate',c_hrtime_t),
        ('wcnt',ctypes.c_uint),
        ('rcnt',ctypes.c_uint),
    ]
kstat_io_t_p = ctypes.POINTER(kstat_io_t)


class KStatFunction(WrappedFunction):
    @classmethod
    def get_library_name(cls):
        if sys.maxsize < 2 ** 32:
            libdir = 'lib'
        else:
            platform_string = get_platform_string()
            if 'x64' in platform_string:
                libdir = 'lib/amd64'
            elif 'sparc' in platform_string:
                libdir = 'lib/sparcv9'
            else:
                return ''
        return '/{}/libkstat.so'.format(libdir)

    @classmethod
    def get_errcheck(cls):
        return errcheck_nothing()

    @classmethod
    def _get_library(cls):
        return ctypes.cdll.LoadLibrary(cls.get_library_name())


class kstat_open(KStatFunction):
    return_value = kstat_ctl_t_p

    @classmethod
    def get_parameters(cls):
        return ()

class kstat_close(KStatFunction):
    return_value = ctypes.c_int

    @classmethod
    def get_parameters(cls):
        return ((kstat_ctl_t_p, IN),)

class kstat_read(KStatFunction):
    return_value = c_kid_t

    @classmethod
    def get_parameters(cls):
        return ((kstat_ctl_t_p, IN),
                (kstat_t_p, IN),
                (kstat_io_t_p, IN_OUT))

@contextmanager
def kstat_context():
    ks = kstat_open()
    try:
        yield ks
    except:
        kstat_close(ks)

class KStat(object):
    def _get_path_statistics(self, ks, kc):
        iostats = kstat_io_t()
        kstat_read(ks, kc, ctypes.byref(iostats)) # TODO Check return value
        return PathStatistics(iostats.nread, iostats.nwritten, iostats.reads, iostats.writes)

    def ks_name_to_human_readable(self, ks_name):
        from re import findall
        res = findall("(.*)\.t(.*)\.(fp.*)", ks_name)
        if len(res) != 1:
            return
        dev_name, target_pid, fp = res[0]
        inst_to_path = DeviceManager.get_inst_to_path_mapping()
        path_to_cfg = DeviceManager.get_path_to_cfg_mapping()
        dev_path = inst_to_path[dev_name]
        ctrl_path = inst_to_path[fp]
        ctrl_inst = path_to_cfg[ctrl_path]
        target = drvpid2port(int(target_pid))
        return dev_path, target, ctrl_inst


    @cached_method
    def get_io_stats(self):
        res = {}
        with kstat_context() as ks:
            elem = ks.contents.kc_chain.contents
            while True:
                if elem and elem.ks_type == KSTAT_TYPE_IO:
                    human_readable = self.ks_name_to_human_readable(elem.ks_name)
                    if human_readable:
                        dev_path, target, ctrl =  human_readable
                        res.setdefault(dev_path, {}).setdefault(ctrl, {}).setdefault(target, self._get_path_statistics(ks, elem))
                if not elem.ks_next:
                    break
                elem = elem.ks_next.contents
        return res


c_caddr = ctypes.c_char_p
MAXNAMELEN = 256
MAXPATHLEN = 1024

class sv_iocdata_t(ctypes.Structure):
    _fields_ = [
        ('client', c_caddr),
        ('phci', c_caddr),
        ('addr', c_caddr),
        ('buf_elem', ctypes.c_uint),
        ('ret_buf', ctypes.c_void_p),
        ('ret_elem', ctypes.c_uint),
    ]
sv_iocdata_t_p = ctypes.POINTER(sv_iocdata_t)


def drvpid2port(pid):
    from fcntl import ioctl

    libc = ctypes.CDLL("libc.so")
    SCSI_VHCI_CTL_SUB_CMD  = ord('x') << 8
    SCSI_VHCI_GET_TARGET_LONGNAME = SCSI_VHCI_CTL_SUB_CMD + 0x0F

    iocdata = sv_iocdata_t()
    iocdata.buf_elem = pid
    iocdata.addr = ctypes.cast(ctypes.create_string_buffer(MAXNAMELEN), ctypes.c_char_p)
    with open("/devices/scsi_vhci:devctl", 'rb') as block_device:
        ioctl(block_device, SCSI_VHCI_GET_TARGET_LONGNAME, iocdata)
    return iocdata.addr
