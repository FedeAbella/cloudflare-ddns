from cloudflare import APIConnectionError, APIStatusError

from logger import logger


class DNS:
    def __init__(self, id, name, ip):
        self.id = id
        self.name = name
        self.ip = ip

    def __repr__(self):
        return f"DNS(id={self.id}, name={self.name}, ip={self.ip})"


def log_api_connection_error(e):
    logger.error(f"Failed to connect to Cloudflare: {e.__cause__}")


def log_api_status_error(e):
    logger.error(
        f"Cloudflare returned non-success status: {e.status_code}, {e.response}"
    )


def log_error(e):
    logger.error(f"Some other error occurred connecting to Clouflare: {e}")


def make_cf_callout(operation, *args):
    try:
        return operation(*args)
    except APIConnectionError as e:
        log_api_connection_error(e)
    except APIStatusError as e:
        log_api_status_error(e)
    except Exception as e:
        log_error(e)

    return None


def z(client, zone_id):
    zone_name = client.zones.get(zone_id=zone_id).to_dict()["name"]
    assert isinstance(
        zone_name, str
    ), f"retrieved zone name is not a string: {zone_name}"

    return zone_name


def d(client, zone_id):
    zone_dns = client.dns.records.list(zone_id=zone_id).to_dict()["result"]
    assert isinstance(
        zone_dns, list
    ), f"retrieved zone dns records is not a list: {zone_dns}"

    return [
        DNS(dns["id"], dns["name"], dns["content"])
        for dns in zone_dns
        if dns["type"] == "A"
    ]


def b(client, zone_id, records):
    patches = [{"id": record.id, "content": record.ip} for record in records]
    response_patches = client.dns.records.batch(
        zone_id=zone_id, patches=patches
    ).to_dict()["patches"]

    assert isinstance(
        response_patches, list
    ), f"patch response records is not a list: {response_patches}"

    return [
        DNS(patch["id"], patch["name"], patch["content"])
        for patch in response_patches
    ]


def get_zone_name(client, zone_id):
    return make_cf_callout(z, client, zone_id)


def get_dns(client, zone_id):
    return make_cf_callout(d, client, zone_id)


def batch_update(client, zone_id, records):
    return make_cf_callout(b, client, zone_id, records)
