import logging
import time
from json import load
from os import getenv
from re import fullmatch

import httpx
import schedule
from cloudflare import Client

from cloudflare_caller import batch_update, get_dns, get_zone_name
from constants import (CF_BASE_URL, DEFAULT_RUN_TIME_SECONDS, DOMAIN_FILE,
                       DOMAIN_PATTERN, IP_PATTERN, IP_URLS)

API_TOKEN = getenv("API_TOKEN")
ZONE_ID = getenv("ZONE_ID")
RUN_EVERY = int(getenv("RUN_EVERY", DEFAULT_RUN_TIME_SECONDS))

CF_CLIENT = Client(api_token=API_TOKEN, base_url=CF_BASE_URL)


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
fh = logging.StreamHandler()
fh_formatter = logging.Formatter("%(asctime)s :: %(levelname)s :: %(message)s")
fh.setFormatter(fh_formatter)
logger.addHandler(fh)


def get_local_ip():
    for url in IP_URLS:
        try:
            ip_response = httpx.get(url)
            if ip_response.status_code == httpx.codes.OK:
                local_ip = ip_response.text.strip()
                assert (
                    fullmatch(IP_PATTERN, local_ip) is not None
                ), f"retrieved local ip does not match ipv4 format: {local_ip}"
                return local_ip
            logger.warning(
                f"Failed to get ip from {url}, status code: {ip_response.status_code}"
            )
        except Exception as e:
            logger.warning(f"Failed to get ip from {url}, with exception {e}")

    return None


def get_domains_to_update(zone_name):
    with open(DOMAIN_FILE) as f:
        domains_to_update = load(f)

    assert isinstance(
        domains_to_update, list
    ), "domains file did not contain a list"

    for domain in domains_to_update:
        assert isinstance(domain, str), f"domain {domain} is not a string"
        assert (
            fullmatch(DOMAIN_PATTERN, domain) is not None
        ), f"domain {domain} does not match subdomain regex pattern"

    return set(
        [
            f"{domain}.{zone_name}" if domain != "@" else f"{zone_name}"
            for domain in domains_to_update
        ]
    )


def update_domains(zone_name):
    try:
        domains_to_update = get_domains_to_update(zone_name)
    except AssertionError as e:
        logger.error("Failed to load domains from json file: ", e)
        return

    if len(domains_to_update) == 0:
        logger.warning("No domains in json file")
        return

    local_ip = get_local_ip()
    if local_ip is None:
        logger.error("Could not get a local ip")
        return
    logger.info(f"Current IP: {local_ip}")

    cf_dns = get_dns(CF_CLIENT, ZONE_ID)
    if cf_dns is None:
        logger.error("Could not fetch Cloudflare domains")
        return

    if len(cf_dns) == 0:
        logger.warning("No domains found in Cloudflare Zone")
        return

    unmatched_domains = domains_to_update.difference(
        set([dns.name for dns in cf_dns])
    )
    for unmatched in unmatched_domains:
        logger.warning(f"Domain {unmatched} not found in Cloudflare zone")

    if len(unmatched_domains) == len(domains_to_update):
        logger.warning(
            "No matched domains in Cloudflare zone. Nothing to update"
        )
        return

    dns_to_update = [
        dns
        for dns in cf_dns
        if dns.name in domains_to_update and dns.ip != local_ip
    ]

    if len(dns_to_update) == 0:
        logger.info(f"All Cloudflare domains point to current IP {local_ip}")
        return

    for dns in dns_to_update:
        dns.ip = local_ip

    updated_dns = batch_update(CF_CLIENT, ZONE_ID, dns_to_update)

    if updated_dns is None:
        logger.warning(
            "Failed to update DNS records. Check previous messages for errors"
        )
        return

    for dns in updated_dns:
        logger.info(f"Updated {dns.name} to IP {dns.ip}")


def main():
    zone_name = get_zone_name(CF_CLIENT, ZONE_ID)

    if zone_name is None:
        logger.critical(
            f"Failed to find requested CF Zone {ZONE_ID}. Quitting."
        )
        return

    logger.info(f"Client set up and using zone: {zone_name}")
    logger.info(f"Updating DNS records now and every {RUN_EVERY} seconds")

    update_domains(zone_name)

    schedule.every(RUN_EVERY).seconds.do(update_domains, zone_name)
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
