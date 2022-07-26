from infi.pyutils.contexts import contextmanager


@contextmanager
def with_host(client, host):
    from .patches import storagemodel, hbaapi, iscsiapi, nvmeapi
    with hbaapi.with_host(client, host), storagemodel.with_host(client, host), iscsiapi.with_host(client, host), nvmeapi.with_host(client, host):
        yield


def install_all_property_collectors_on_client(client):
    from .patches import storagemodel, hbaapi, iscsiapi, nvmeapi
    storagemodel.install_property_collectors_on_client(client)
    hbaapi.install_property_collectors_on_client(client)
    iscsiapi.install_property_collectors_on_client(client)
    nvmeapi.install_property_collectors_on_client(client)


def fetch_all_property_collectors(client):
    for property_collector in client.property_collectors.values():
        property_collector.get_properties()
