from infi.storagemodel import unix, errors
from unittest import SkipTest
from infi.unittest import TestCase, parameters
from mock import patch

class MockModel(unix.UnixStorageModel):
    def rescan_method(self):
        pass


class MockModelWithException(unix.UnixStorageModel):
    def rescan_method(self):
        raise RuntimeError()


class StuckMockModel(unix.UnixStorageModel):
    rescan_subprocess_timeout = 0.01

    def rescan_method(self):
        from time import sleep
        sleep(10)


class AMultiprocessingRescanTestCase(TestCase):  # this test cases needs to be executed before the gipc one
    @classmethod
    def setUpClass(cls):
        cls.prepare_patch()

    @classmethod
    def prepare_patch(cls):
        cls.gevent_wrapper_patch = patch("infi.storagemodel.base.gevent_wrapper")
        gevent_wrapper = cls.gevent_wrapper_patch.__enter__()
        gevent_wrapper.get_process_class.side_effect = cls.get_process_class
        gevent_wrapper.start_process.side_effect = cls.start_process
        gevent_wrapper.sleep.side_effect = cls.sleep

    @classmethod
    def teardownClass(cls):
        if getattr(cls, 'gevent_wrapper_patch'):
            cls.gevent_wrapper_patch.__exit__(None, None, None)

    @staticmethod
    def get_process_class():
        from multiprocessing import Process
        return Process

    @staticmethod
    def start_process(target, *args, **kwargs):
        from multiprocessing import Process
        process = Process(target=target, args=args, kwargs=kwargs)
        process.start()
        return process

    @staticmethod
    def sleep(n):
        from time import sleep
        sleep(n)

    @parameters.iterate("wait_for_completion", [True, False])
    @parameters.iterate("raise_error", [True, False])
    def test_simple_model(self, wait_for_completion, raise_error):
        model = MockModel()
        model._initiate_rescan(wait_for_completion=wait_for_completion, raise_error=raise_error)

    def test_exception_in_rescan_method(self):
        model = MockModelWithException()
        model._initiate_rescan(wait_for_completion=True, raise_error=False)
        with self.assertRaises(errors.RescanError):
            model._initiate_rescan(wait_for_completion=True, raise_error=True)
        model._initiate_rescan(wait_for_completion=False, raise_error=False)
        with self.assertRaises(errors.RescanError):
            model._initiate_rescan(wait_for_completion=True, raise_error=True)

    def test_rescan_method_that_does_not_stop(self):
        model = StuckMockModel()
        model._initiate_rescan(wait_for_completion=True, raise_error=True)
        model._initiate_rescan(wait_for_completion=True, raise_error=False)


class GIPC_RescanTestCase(AMultiprocessingRescanTestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from gevent import sleep
            from gipc.gipc import start_process, _GProcess
            cls.prepare_patch()
        except ImportError:
            cls.gevent_wrapper_patch = None
            raise SkipTest("gevent/gipc import error")

    @staticmethod
    def get_process_class():
        from gipc.gipc import _GProcess as Process
        return Process

    @staticmethod
    def start_process(target, *args, **kwargs):
        from gipc.gipc import start_process as _start_process
        return _start_process(target, args=args, kwargs=kwargs)

    @staticmethod
    def sleep(n):
        from gevent import sleep
        return sleep(n)
