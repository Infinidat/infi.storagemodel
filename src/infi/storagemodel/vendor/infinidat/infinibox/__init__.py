from logging import getLogger
log = getLogger(__name__)

NFINIDAT_IEEE = 0x742B0F
ALIGNMENT = 64*1024
vid_pid = ("NFINIDAT", "InfiniBox")
vid_pid_with_spaces = ("NFINIDAT".ljust(8), "InfiniBox".ljust(16))
