
from infi.exceptools import InfiException

class StorageModelError(InfiException):
    """ """
    pass

class StorageModelFindError(StorageModelError):
    """ """
    pass

class TimeoutError(StorageModelError):
    """ """
    pass
