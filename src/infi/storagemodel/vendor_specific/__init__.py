
class VendorSpecificFactory(object):
    __mixins__ = dict()
    __initialized__ = False

    def __init__(self):
        super(VendorSpecificFactory, self).__init__()
        if not VendorSpecificFactory.__initialized__:
            self._add_inbox_mixins()
            self.__initialized__ = True

    def _add_inbox_mixins(self):
        from .infinibox import InfiniBoxMixin
        VendorSpecificFactory.__mixins__[("NFINIDAT", "InfiniBox")] = InfiniBoxMixin

    def _create_mixin(self, original, mixin_class):
        raise NotImplementedError

    def create_mixin_object(self, original):
        vendor_id, product_id = original.standard_inquiry_data.vendor_id, original.standard_inquiry_data.product_id
        mixin_class = VendorSpecificFactory.__mixins__.get((vendor_id, product_id), None)
        if mixin_class is None:
            return None
        return self._create_mixin(original, mixin_class)

    def get_mixin_class_by_vid_pid(self, vid, pid):
        return VendorSpecificFactory.__mixins__[(vid, pid)]

    def iter_available_mixin_classes(self):
        for k, v in self.__mixins__.iteritems():
            yield k, v

    def set_mixin_class(self, vid, pid, mixin_class):
        VendorSpecificFactory.__mixins__[(vid, pid)] = mixin_class
