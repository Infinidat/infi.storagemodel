from infi.pyutils.lazy import cached_method
from infi.storagemodel.unix.utils import execute_command_safe
import re

def get_scsi_device_info(dev_path):
    REGEXP = r"OS Device Name:\s*[\w\/]*{}\s*".format(dev_path) + \
             r"((((?:HBA Port WWN: \w+\s*(Remote Port WWN: \w+\s*)+)+)LUN:\s*(\d+)\s*)+\s*)+" + \
             r"Vendor:\s*\w+\s*Product:\s*\w+\s*Device Type:\s*"
    pattern = re.compile(REGEXP, re.MULTILINE | re.DOTALL)
    output = execute_command_safe("fcinfo lu -v")
    return pattern.search(output).group(1)

def get_device_wwns_and_lun(dev_path):
    device_info = get_scsi_device_info(dev_path)
    for hosts_and_targets, lun in re.findall("((?:(?:HBA Port WWN: \w+(?:\s*Remote Port WWN: \w+)+)\s*)+)LUN:\s*(\d+)", device_info):
        for host_wwn, target_info in re.findall("HBA Port WWN: (\w+)((?:\s*Remote Port WWN: \w+)+)", hosts_and_targets):
            for target_wwn in re.findall("Remote Port WWN: (\w+)", target_info):
                yield (host_wwn, target_wwn, lun)

def get_path_lun(dev_path, hba_port_wwn, target_port_wwn):
    for host_wwn, target_wwn, lun in get_device_wwns_and_lun(dev_path):
        if host_wwn == hba_port_wwn and target_wwn == target_port_wwn:
            return int(lun)
