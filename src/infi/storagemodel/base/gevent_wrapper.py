from infi.pyutils.contexts import contextmanager
from logging import getLogger

logger = getLogger(__name__)

try:
    from gevent import sleep
    from gevent import getcurrent as get_id
    from gevent.event import Event
    is_thread_alive = lambda greenlet: not greenlet.dead
except ImportError:
    from time import sleep
    from threading import Event
    try:
        from thread import get_ident as get_id
    except ImportError:
        from threading import get_ident as get_id
    is_thread_alive = lambda thread: thread.is_alive()


def spawn(target, *args, **kwargs):
    try:
        from gevent import spawn as _spawn
        return _spawn(target, *args, **kwargs)
    except ImportError:
        from threading import Thread
        thread = Thread(target=target, args=args, kwargs=kwargs)
        thread.start()
        return thread


try:
    from infi.gevent_utils.deferred import create_threadpool_executed_func as defer
    from infi.gevent_utils.silent_greenlets import spawn, joinall
except ImportError:
    defer = lambda func: func
    def joinall(threads, timeout=None, raise_error=False):
        # TODO treat timeout and raise_error
        [thread.join() for thread in threads]


def run_together(callables):
    joinall([spawn(item) for item in callables], raise_error=True)



def reinit():
    try:
        from gevent import reinit as _reinit
        _reinit()
    except ImportError:
        pass


from infi.blocking import make_blocking, blocking_context, Timeout
