Python-based SCSI inquiry utility
---------------------------------

There are two implementations:

* `naive.py`; uses the high-level APIs in `infi.storagemodel`
* `low-level.py`; uses lower-level interfaces that are being used within `infi.storagemodel`; this implementation is longer than the naive one, but it is more efficient (sends less SCSI commands behind the scenes)
