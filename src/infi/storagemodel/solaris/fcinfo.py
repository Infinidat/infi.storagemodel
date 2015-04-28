from infi.pyutils.lazy import cached_method
from infi.storagemodel.unix.utils import execute_command_safe
import re

def get_scsi_device_info(dev_path):
    REGEXP = r"^\s*OS Device Name:\s*[\w\/]*{}\s*".format(dev_path) + \
             r"(HBA Port WWN: \w+\s*(Remote Port WWN: \w+\s*LUN:\s*([0-9]+)\s*)+\s*)+" + \
             r"Vendor:\s*\w+\s*Product:\s*\w+\s*Device Type:\s*"
    pattern = re.compile(REGEXP, re.MULTILINE | re.DOTALL)
    output = execute_command_safe("fcinfo lu -v")
    return pattern.findall(output)[0][0]

def get_hba_port_info_from_device_info(dev_path, hba_port_wwn):
    REGEXP = r"(HBA Port WWN: \w+\s*(Remote Port WWN: \w+\s*LUN:\s*([0-9]+)\s*)+\s*)+".format(hba_port_wwn)
    pattern = re.compile(REGEXP, re.MULTILINE | re.DOTALL)
    device_info = get_scsi_device_info(dev_path)
    return pattern.findall(device_info)[0][0]

def get_path_lun(dev_path, hba_port_wwn, target_port_wwn):
    REGEXP = r"\s*Remote Port WWN: {}\s*LUN:\s*([0-9]+)$".format(target_port_wwn)
    pattern = re.compile(REGEXP, re.MULTILINE | re.DOTALL)
    hba_port_info = get_hba_port_info_from_device_info(dev_path, hba_port_wwn)
    return int(pattern.findall(hba_port_info)[0])
