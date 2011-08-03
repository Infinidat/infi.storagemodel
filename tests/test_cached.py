from unittest import TestCase

from infi.pyutils.lazy import cached_property, cached_method, clear_cache, populate_cache

class TestSubject(object):
    def __init__(self):
        self._counter = 0

    @cached_property
    def counter(self):
        self._counter += 1
        return self._counter

    @cached_method
    def get_counter(self):
        """some documentation"""
        self._counter += 1
        return self._counter

    @cached_method
    def is_equal(self, number):
        return self._counter == number

class CachedPropertyTestCase(TestCase):
    def setUp(self):
        self.subject = TestSubject()

    def test_cached_property(self):
        self.assertEqual(self.subject.counter, 1)
        self.assertEqual(self.subject.counter, 1)

    def test_clear_cache(self):
        self.assertEqual(self.subject.counter, 1)
        clear_cache(self.subject)
        self.assertEqual(self.subject.counter, 2)

    def test_populate_cache(self):
        self.assertEqual(self.subject._counter, 0)
        populate_cache(self.subject)
        self.assertEqual(self.subject._counter, 2)

class CachedMethodTestCase(TestCase):
    def setUp(self):
        self.subject = TestSubject()

    def test_cached_value(self):
        self.assertEqual(self.subject.get_counter(), 1)
        self.assertEqual(self.subject.get_counter(), 1)

    def test_clear_cache(self):
        self.assertEqual(self.subject.get_counter(), 1)
        clear_cache(self.subject)
        self.assertEqual(self.subject.get_counter(), 2)

    def test_doc(self):
        self.assertEqual(self.subject.get_counter.__doc__, "some documentation")

    def test_name(self):
        self.assertEqual(self.subject.get_counter.__name__, "get_counter")

    def test_is_equal(self):
        self.assertEqual(self.subject.is_equal(0), True)
        self.subject.get_counter()
        self.assertEqual(self.subject.is_equal(0), True)
        self.assertEqual(self.subject.is_equal(1), True)
        self.assertEqual(self.subject.is_equal(0), True)

