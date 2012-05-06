__import__("pkg_resources").declare_namespace(__name__)

__all__ = [ 'get_storage_model' ]

__storage_model = None

def _get_platform_specific_storagemodel_class():
    from platform import system # do platform-specific magic here.
    plat = system().lower().replace('-', '')
    from .base import StorageModel as PlatformStorageModel # helps IDEs
    from brownie.importing import import_string
    platform_module_string = "{}.{}".format(__name__, plat)
    platform_module = import_string(platform_module_string)
    PlatformStorageModel = getattr(platform_module, "{}StorageModel".format(plat.capitalize()))
    return PlatformStorageModel

def get_storage_model():
    """returns a global instance of a StorageModel"""
    # pylint: disable=W0603,C0103
    global __storage_model
    if __storage_model is None:
        PlatformStorageModel = _get_platform_specific_storagemodel_class()
        __storage_model = PlatformStorageModel()
    return __storage_model
