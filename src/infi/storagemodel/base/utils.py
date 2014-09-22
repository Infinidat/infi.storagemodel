from logging import getLogger


logger = getLogger(__name__)


class Utils(object):
    #############################
    # Platform Specific Methods #
    #############################

    def get_free_space(self, path):  # pragma: no cover
        """Returns the free space in bytes, inside the filesystem of a given path"""
        # platform implementation
        raise NotImplementedError()