__import__("pkg_resources").declare_namespace(__name__)

__all__ = [ 'get_storage_model' ]

__storage_model = None

def get_storage_model():
    """returns a global instance of a StorageModel"""
    global __storage_model
    if __storage_model is None:
        # do platform-specific magic here.
        from platform import system
        plat = system().lower().replace('-', '')
        from .base import StorageModel as PlatformStorageModel # helps IDEs
        exec "from .%s import %sStorageModel as PlatformStorageModel" % (plat, plat.capitalize())
        __storage_model = PlatformStorageModel()
    return __storage_model
