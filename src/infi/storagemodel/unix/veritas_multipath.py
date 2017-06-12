from infi.storagemodel.unix.utils import execute_command_safe
from infi.storagemodel.base import multipath, gevent_wrapper
from infi.pyutils.lazy import cached_method
from contextlib import contextmanager
from munch import Munch

from logging import getLogger
logger = getLogger(__name__)


def is_veritas_multipathing_installed():
    from os import path, environ
    veritas_executables = ('vxdmpadm',)
    return environ.get("VMPATH") or \
           any(path.exists(path.join(path.sep, "usr", "sbin", basename)) for basename in veritas_executables) or \
           bool(environ.get("MOCK_VERITAS"))


class VeritasMultipathEntry(Munch):
    def __init__(self, dmp_name, paths, vendor_id, product_id):
        self.paths = paths
        self.dmp_name = dmp_name
        self.vendor_id = vendor_id
        self.product_id = product_id


class VeritasSinglePathEntry(Munch):
    def __init__(self, sd_device_name, ctlr, state, wwn):
        self.sd_device_name = sd_device_name
        self.ctlr = ctlr
        self.state = state
        self.wwn = wwn


class VeritasMultipathClient(object):
    def get_list_of_multipath_devices(self):
        multipaths = []
        multipath_dicts = self.parse_paths_list(self.read_paths_list())
        for multi in multipath_dicts:
            paths = [VeritasSinglePathEntry(p['name'], p['ctlr'], p['state'], p['aportWWN']) for p in multi['paths']]
            multipaths.append(VeritasMultipathEntry(multi['dmpdev'], paths, multi['vid'], multi['pid']))
        return multipaths

    def read_paths_list(self):
        return execute_command_safe("vxdmpadm list dmpnode") if is_veritas_multipathing_installed() else ""

    def parse_paths_list(self, paths_list_output):
        from re import compile, MULTILINE, DOTALL
        MULTIPATH_PATTERN = r"^dmpdev\s*=\s*(?P<dmpdev>\w+)\n" + \
                            r"^state\s*=\s*(?P<state>\w+)\n" + \
                            r"^enclosure\s*=\s*(?P<enclosure>\w+)\n" + \
                            r"^cab-sno\s*=\s*(?P<cab_sno>\w+)\n" + \
                            r"^asl\s*=\s*(?P<asl>[\w\.]+)\n" + \
                            r"^vid\s*=\s*(?P<vid>\w+)\n" + \
                            r"^pid\s*=\s*(?P<pid>[\w ]+)\n" + \
                            r"^array-name\s*=\s*(?P<array_name>\w+)\n" + \
                            r"^array-type\s*=\s*(?P<array_type>[\w/]+)\n" + \
                            r"^iopolicy\s*=\s*(?P<iopolicy>\w+)\n" + \
                            r"^avid\s*=\s*(?P<avid>[-\w]+)\n" + \
                            r"^lun-sno\s*=\s*(?P<lun_sno>\w*)\n" + \
                            r"^udid\s*=\s*(?P<udid>[\w%\.-]+)\n" + \
                            r"^dev-attr\s*=\s*(?P<dev_attr>[ \-\w]+)\n" + \
                            r"(^lun_type\s*=\s*(?P<lun_type>[-\w]+)\n)?" + \
                            r"(^scsi3_vpd\s*=\s*(?P<scsi3_vpd>[-\w\:]+)\n)?" + \
                            r"(^raid_type\s*=\s*(?P<raid_type>\w+)\n)?" + \
                            r"(^replicated\s*=\s*(?P<replicated>\w+)\n)?" + \
                            r"(^num_paths\s*=\s*(?P<num_paths>\w+)\n)?" + \
                            r"^###path\s*=[\s\w]+\n" + \
                            r"(?P<paths>(?:^path\s*=\s*[\w -\:\(\)\@\/\,]+\n)*)"
        pattern = compile(MULTIPATH_PATTERN, MULTILINE | DOTALL)
        matches = []
        for match in pattern.finditer(paths_list_output):
            logger.debug("multipath found: %s", match.groupdict())
            multipath_dict = dict((key, value if value is not None else value) \
                              for (key, value) in match.groupdict().items())
            self.parse_paths_in_multipath_dict(multipath_dict)
            matches.append(multipath_dict)
        return matches

    def parse_paths_in_multipath_dict(self, multipath_dict):
        from re import compile, MULTILINE, DOTALL
        PATH_PATTERN = r"^path\s*=\s*" + \
            r"(?P<name>[\w]+)\s*" + \
            r"(?P<state>[\w\(\)]+)\s*" + \
            r"(?P<type>[\w-]+)\s*" + \
            r"(?P<transport>[\w]+)\s*" + \
            r"(?P<ctlr>[\w]+)\s*" + \
            r"(?P<hwpath>[\w\/\@\,]+)\s*" + \
            r"(?P<aportID>[\w-]+)\s*" + \
            r"(?P<aportWWN>[\w:]+)\s*" + \
            r"(?P<attr>[\w-]+)\s*"
        pattern = compile(PATH_PATTERN, MULTILINE | DOTALL)
        matches = []
        for match in pattern.finditer(multipath_dict['paths']):
            logger.debug("paths found: %s", match.groupdict())
            pathgroup_dict = dict((key, value if value is not None else value) for (key, value) in match.groupdict().items())
            matches.append(pathgroup_dict)
        multipath_dict['paths'] = matches
