from unittest import TestCase

from infi.storagemodel.utils import cached_property

class CachedTestCase(TestCase):
    def test_cached_property(self):
        class Foo(object):
            def __init__(self):
                self.my_foo = 5
                
            @cached_property
            def foo(self):
                self.my_foo += 1
                return self.my_foo
            
        f = Foo()
        self.assertEqual(f.foo, 6)
        self.assertEqual(f.foo, 6)
