import infi.iscsiapi
from infi.iscsiapi import base
from infi.pyutils.contexts import contextmanager
from infi.pyutils.patch import monkey_patch
from infi.storagemodel.vmware.patches.storagemodel import get_stack_trace
from traceback import extract_stack
from logging import getLogger


logger = getLogger(__name__)


def install_property_collectors_on_client(client):
    pass


@contextmanager
def with_host(client, host):
    from traceback import extract_stack
    from infi.pyvmomi_wrapper import get_reference_to_managed_object
    monkey_patch(infi.iscsiapi, "get_iscsiapi", ConnectionManagerFactory.get)
    previous = ConnectionManagerFactory.get()
    stack_trace = get_stack_trace()
    caller = extract_stack(stack_trace, 6)[1][2]
    moref = get_reference_to_managed_object(host)
    try:
        current = ConnectionManagerFactory.set(ConnectionManagerFactory.create(client, host))
        if previous is current:
            logger.debug("entered context for the same host {} as part of {}".format(moref, caller))
        else:
            logger.debug("entered context for host {} as part of {}".format(moref, caller))
        yield
    finally:
        logger.debug("exited context for host {} as part of {}".format(moref, caller))
        ConnectionManagerFactory.set(previous)


class ConnectionManager(base.ConnectionManager):
    def __init__(self, client, moref):
        super(ConnectionManager, self).__init__()
        self._moref = moref
        self._client = client

    def _install_property_collector(self):
        install_property_collectors_on_client(self._client)

    def get_sessions(self, target=None):
        return []


class ConnectionManagerFactory(object):
    models_by_host_value = {}
    models_by_greenlet = {}

    @classmethod
    def clear(cls):
        cls.models_by_greenlet.clear()
        cls.models_by_host_value.clear()

    @classmethod
    def create(cls, client, hostsystem):
        from infi.pyvmomi_wrapper import get_reference_to_managed_object
        key = get_reference_to_managed_object(hostsystem)
        if key not in cls.models_by_host_value:
            value = ConnectionManager(client, key)
            cls.models_by_host_value[key] = value
        return cls.models_by_host_value[key]

    @classmethod
    def get_id(cls):
        from infi.storagemodel.base.gevent_wrapper import get_id
        return get_id()

    @classmethod
    def get(cls):
        return cls.models_by_greenlet.get(cls.get_id())

    @classmethod
    def set(cls, value):
        current = cls.get_id()
        if value is None:
            try:
                del cls.models_by_greenlet[current]
            except KeyError:
                pass
        else:
            cls.models_by_greenlet[current] = value
        return value
