
class FiberChannelMixin(object):
    pass

class iSCSIMixin(object):
    pass

class ConnectivityFactory(object):
    def create_mixin_object(self, original):
        # how do we know if this is iscsi or fiber?
        raise NotImplementedError
