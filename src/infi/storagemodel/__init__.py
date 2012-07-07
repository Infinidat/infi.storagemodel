__import__("pkg_resources").declare_namespace(__name__)

__all__ = [ 'get_storage_model' ]

__storage_model = None

from logging import getLogger
from infi.exceptools import chain
logger = getLogger(__name__)

def get_platform_name():
    from platform import system
    plat = system().lower().replace('-', '')
    return plat

def _get_platform_specific_storagemodel_class():
    # do platform-specific magic here.
    from .base import StorageModel as PlatformStorageModel # helps IDEs
    from brownie.importing import import_string
    plat = get_platform_name()
    platform_module_string = "{}.{}".format(__name__, plat)
    platform_module = import_string(platform_module_string)
    try:
        PlatformStorageModel = getattr(platform_module, "{}StorageModel".format(plat.capitalize()))
    except AttributeError:
        msg = "Failed to import platform-specific storage model"
        logger.exception(msg)
        raise chain(ImportError(msg))
    return PlatformStorageModel

def _get_platform_specific_storagemodel():
    return _get_platform_specific_storagemodel_class()()

def get_storage_model():
    """returns a global instance of a StorageModel"""
    # pylint: disable=W0603,C0103
    global __storage_model
    if __storage_model is None:
        __storage_model = _get_platform_specific_storagemodel()
    return __storage_model
