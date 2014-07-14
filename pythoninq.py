'''
Created on Jul 11, 2014
@author: aviad@infinidat.com
'''
from infi.storagemodel import get_storage_model
import sys

if __name__ == '__main__':
    pass

    print("\nPython Inquiry utility, Version V0.1 (using storagemodel by INFINIDAT)\n")
    print("-----------------------------------------------------------------------------------------------------------------------------------------------")
    print("DEVICE          \t:VEND     \t:PROD            \t:REV   \t:SER NUM                         \t:CAP(kb)            \t:PATHS")
    print("-----------------------------------------------------------------------------------------------------------------------------------------------")
    
    
    model = get_storage_model();
    scsi = model.get_scsi()
    mpio = model.get_native_multipath()
    mpaths = mpio.get_all_multipath_block_devices()
    block_devices = scsi.get_all_scsi_block_devices()    
    non_mp_disks = mpio.filter_non_multipath_scsi_block_devices(block_devices)
    
    all_devices= non_mp_disks + mpaths
    
    for dev2dis in all_devices:
        sys.stdout.write("%-16s\t" % dev2dis.get_display_name())
        sys.stdout.write(":%-9s\t" % dev2dis.get_scsi_vendor_id())
        sys.stdout.write(":%-16s\t" % dev2dis.get_scsi_product_id())
        sys.stdout.write(":%-6s\t" % dev2dis.get_scsi_revision())
        sys.stdout.write(":%-32s\t" % dev2dis.get_scsi_serial_number())
        sys.stdout.write(":%-16s\t" % str(long(dev2dis.get_size_in_bytes()) /1024) )
        if hasattr(dev2dis, 'get_paths'):
            sys.stdout.write(":%s\t\n" % len(dev2dis.get_paths()))
        else:
            sys.stdout.write(":1\t\n")
        
