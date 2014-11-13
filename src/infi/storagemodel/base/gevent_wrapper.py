from infi.pyutils.contexts import contextmanager


try:
    from gevent import sleep
    from gevent import getcurrent as get_id
    is_thread_alive = lambda greenlet: not greenlet.dead
except ImportError:
    from time import sleep
    from thread import get_ident as get_id
    is_thread_alive = lambda thread: thread.is_alive()


def spawn(target, *args, **kwargs):
    try:
        from gevent import spawn as _spawn
        return _spawn(*args, **kwargs)
    except ImportError:
        from threading import Thread
        thread = Thread(target=target, args=args, kwargs=kwargs)
        thread.start()
        return thread


def start_process(target, *args, **kwargs):
    try:
        from gipc.gipc import _GProcess as Process
        from gipc.gipc import start_process as _start_process
        return _start_process(target, args=args, kwargs=kwargs)
    except ImportError:
        from multiprocessing import Process
        process = Process(target=target, args=args, kwargs=kwargs)
        process.start()
        return process


def get_timeout():
    """ Returns the timeout object and exception class"""
    try:  # gipc-based implementation
        from gevent import Timeout
        return Timeout(TIMEOUT_IN_SEC), Timeout
    except ImportError:
        from Queue import Empty
        return TIMEOUT_IN_SEC, Empty


def reinit():
    try:
        from gevent import reinit as _reinit
        _reinit()
    except ImportError:
        pass


@contextmanager
def get_pipe_context():
    try:
        from gipc.gipc import pipe
        _pipe_context = pipe(duplex=True)
    except ImportError:
        from multiprocessing import Queue
        _pipe_context = Queue()
    with _pipe_context as (reader, writer):
        yield reader, writer
