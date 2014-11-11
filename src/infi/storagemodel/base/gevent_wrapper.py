from infi.pyutils.contexts import contextmanager


try:
    from gevent import sleep
    from gevent import getcurrent as get_id
    from gevent import spawn
    is_thread_alive = lambda gevent: not gevent.dead
except ImportError:
    from time import sleep
    from thread import get_ident as get_id
    def spawn(target, *args, **kwargs):
        from threading import Thread
        thread = Thread(target=target, args=args, kwargs=kwargs)
        thread.start()
        return thread
    is_thread_alive = lambda thread: thread.is_alive()

try:
    from gipc.gipc import _GProcess as Process
    from gipc.gipc import start_process
except ImportError:
    from multiprocessing import Process
    def start_process(target, *args, **kwargs):
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
        from gevent import reinit
        reinit()
    except ImportError:
        pass


@contextmanager
def get_pipe_context():
    try:
        from gipc.gipc import pipe
        _pipe_context = pipe(duplex=True)
    except ImportError:
        _pipe_context = queue()
    with _pipe_context as (reader, writer):
        yield reader, writer
