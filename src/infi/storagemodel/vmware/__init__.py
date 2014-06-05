from infi.pyutils.contexts import contextmanager


@contextmanager
def with_host(host):
    from .patches import storagemodel, hbaapi
    with hbaapi.with_host(host), storagemodel.with_host(host):
        yield


def install_all_property_collectors_on_client(client):
    from .patches import storagemodel, hbaapi
    storagemodel.install_property_collectors_on_client(client)
    hbaapi.install_property_collectors_on_client(client)


def fetch_all_property_collectors(client):
    for property_collector in client.facades.values():
        property_collector.getProperties()
