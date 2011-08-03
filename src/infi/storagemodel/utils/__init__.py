# Adapted from http://wiki.python.org/moin/PythonDecoratorLibrary#Cached_Properties

class cached_property(object):
    """Decorator for read-only properties evaluated only once.

    It can be used to created a cached property like this::

        import random

        # the class containing the property must be a new-style class
        class MyClass(object):
            # create property whose value is cached for ten minutes
            @cached_method
            def randint(self):
                # will only be evaluated every 10 min. at maximum.
                return random.randint(0, 100)

    The value is cached  in the '_cache' attribute of the object inst that
    has the property getter method wrapped by this decorator. The '_cache'
    attribute value is a dictionary which has a key for every property of the
    object which is wrapped by this decorator. Each entry in the cache is
    created only when the property is accessed for the first time and is a
    two-element tuple with the last computed property value and the last time
    it was updated in seconds since the epoch.

    To expire a cached property value manually just do::
    
        del inst._cache[<property name>]
    """
    def __init__(self, fget, doc=None):
        super(cached_property, self).__init__()
        self.fget = fget
        self.__doc__ = doc or fget.__doc__
        self.__name__ = fget.__name__
        self.__module__ = fget.__module__

    def __get__(self, inst, owner):
        try:
            value = inst._cache[self.__name__]
        except (KeyError, AttributeError):
            value = self.fget(inst)
            try:
                cache = inst._cache
            except AttributeError:
                cache = inst._cache = {}
            cache[self.__name__] = value
        return value

class cached_method(object):
    """Decorator that caches a function's return value each time it is called.
    If called later with the same arguments, the cached value is returned, and
    not re-evaluated.
    """
    def __init__(self, func):
        super(cached_method, self).__init__()
        self.func = func
        self.__name__ = func.__name__
        self.__doc__ = func.__doc__
        self.inst = None

    def __call__(self, *args, **kwargs):
        try:
            value = self.inst._cache[self.__name__]
        except (KeyError, AttributeError):
            value = self.func(self.inst, *args, **kwargs)
            try:
                self.inst._cache[self.__name__] = value
            except AttributeError:
                self.inst._cache = {}
                self.inst._cache[self.__name__] = value
        return value

    def __get__(self, obj, objtype):
        self.inst = obj
        return self

def clear_cache(self):
    if hasattr(self, '_cache'):
        getattr(self, '_cache').clear()

def populate_cache(self, attributes_to_skip=["get_vendor"]):
    """ this method attempts to get all the lazy cached properties and methods
    There are two special cases:
    * Some attributes may not be available and raises exceptions.
      If you wish to skip these, pass them in the attributes_to_skip list
    * The calling of cached methods is done without any arguments, and catches TypeError exceptions
      for the case a cached method requires arguments. The exception is logged.
    """
    from inspect import getmembers
    from logging import debug, exception
    for key, value in getmembers(self):
        if key in attributes_to_skip:
            continue
        if isinstance(value, cached_method):
            debug("getting attribute %s from %s", repr(key), repr(self))
            try:
                _ = value()
            except TypeError, e:
                exception(e)

class LazyImmutableDict(object):
    """ Use this object when you have a list of keys but fetching the values is expensive,
    and you want to do it in a lazy fasion"""
    def __init__(self, dict):
        self._dict = dict

    def __getitem__(self, key):
        value = self._dict[key]
        if value is None:
            value = self._dict[key] = self._create_value(key)
        return value

    def keys(self):
        return self._dict.keys()

    def __contains__(self, key):
        return self._dict.__contains__(key)

    def has_key(self, key):
        return self._dict.has_key(key)

    def __len__(self):
        return len(self._dict)

    def _create_value(self, key):
        raise NotImplementedError()

