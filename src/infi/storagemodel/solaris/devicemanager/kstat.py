import sys
import ctypes
from infi.pyutils.contexts import contextmanager
from infi.pyutils.lazy import cached_method
from infi.storagemodel.base.multipath import PathStatistics
from infi.cwrap import WrappedFunction, errcheck_nothing, IN, IN_OUT

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
        return '/lib/amd64/libkstat.so' if sys.maxsize > 2 ** 32 else '/lib/libkstat.so'

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
        return (kstat_ctl_t_p)

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

    @cached_method
    def get_io_stats(self):
        res = {}
        with kstat_context() as ks:
            elem = ks.contents.kc_chain.contents
            while True:
                if elem and elem.ks_type == KSTAT_TYPE_IO:
                    res[elem.ks_name] = self._get_path_statistics(ks, elem)
                if not elem.ks_next:
                    break
                elem = elem.ks_next.contents
        return res
