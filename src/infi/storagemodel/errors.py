
from infi.exceptools import InfiException

class StorageModelError(InfiException):
    """Base Exception class for this module """
    pass

class StorageModelFindError(StorageModelError):
    """Find error"""
    pass

class TimeoutError(StorageModelError):
    """Timeout error"""
    pass

# pylint: disable=E1002
# InfiException inherits from Exception

class NotMounted(StorageModelError):
    def __init__(self, mount_point):
        super(NotMounted, self).__init__("path {!r} is not being used by any mount".format(mount_point))

class AlreadyMounted(StorageModelError):
    def __init__(self, mount_point):
        super(AlreadyMounted, self).__init__("mount point {!r} is already mounted".format(mount_point))

class MountPointDoesNotExist(StorageModelError):
    def __init__(self, mount_point):
        super(MountPointDoesNotExist, self).__init__("mount point {!r} does not exist".format(mount_point))

class MountPointInUse(StorageModelError):
    def __init__(self, mount_point):
        super(MountPointInUse, self).__init__("mount point {!r} is already in use".format(mount_point))
