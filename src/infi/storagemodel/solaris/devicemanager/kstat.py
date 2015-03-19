from ctypes import *
from logging import getLogger

logger = getLogger(__name__)

"""
from /usr/include/sys/kstat.h

#define	KSTAT_IOC_BASE		('K' << 8)
#define	KSTAT_IOC_CHAIN_ID	KSTAT_IOC_BASE | 0x01
#define	KSTAT_IOC_READ		KSTAT_IOC_BASE | 0x02
#define	KSTAT_IOC_WRITE		KSTAT_IOC_BASE | 0x03

#define	KSTAT_STRLEN	31	/* 30 chars + NULL; must be 16 * n - 1 */

/* The generic kstat header */

typedef struct kstat {
	/*
	 * Fields relevant to both kernel and user
	 */
	hrtime_t	ks_crtime;	/* creation time (from gethrtime()) */
	struct kstat	*ks_next;	/* kstat chain linkage */
	kid_t		ks_kid;		/* unique kstat ID */
	char		ks_module[KSTAT_STRLEN]; /* provider module name */
	uchar_t		ks_resv;	/* reserved, currently just padding */
	int		ks_instance;	/* provider module's instance */
	char		ks_name[KSTAT_STRLEN]; /* kstat name */
	uchar_t		ks_type;	/* kstat data type */
	char		ks_class[KSTAT_STRLEN]; /* kstat class */
	uchar_t		ks_flags;	/* kstat flags */
	void		*ks_data;	/* kstat type-specific data */
	uint_t		ks_ndata;	/* # of type-specific data records */
	size_t		ks_data_size;	/* total size of kstat data section */
	hrtime_t	ks_snaptime;	/* time of last data shapshot */
	/*
	 * Fields relevant to kernel only
	 */
	int		(*ks_update)(struct kstat *, int); /* dynamic update */
	void		*ks_private;	/* arbitrary provider-private data */
	int		(*ks_snapshot)(struct kstat *, void *, int);
	void		*ks_lock;	/* protects this kstat's data */
} kstat_t;


"""

KSTAT_STRLEN = 31

c_kid_t = c_int
c_kstat_string = c_char * KSTAT_STRLEN
c_hrtime_t = c_longlong

class _kstat_t(Structure):
    pass

_kstat_t_p = POINTER(_kstat_t)

_kstat_t._fields_ = [
    ('ks_crtime', c_hrtime_t),
    ('ks_next', _kstat_t_p),
    ('ks_kid', c_kid_t),
    ('ks_module', c_kstat_string),
    ('ks_resv', c_ubyte),
    ('ks_instance', c_int),
    ('ks_name', c_kstat_string),
    ('ks_type', c_ubyte),
    ('ks_class', c_kstat_string),
    ('ks_flags', c_ubyte),
    ('ks_data', c_void_p),
    ('ks_ndata', c_uint),
    ('ks_data_size', c_size_t),
    ('ks_snaptime', c_hrtime_t),
    ('ks_update', c_void_p),
    ('ks_private', c_void_p),
    ('ks_snapshot', c_void_p),
    ('ks_lock', c_void_p)
]
