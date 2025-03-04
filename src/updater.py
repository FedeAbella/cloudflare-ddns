import time
from datetime import datetime
from json import load
from os import getenv
from re import fullmatch

import httpx
import schedule
from cloudflare import Client
from dotenv import load_dotenv

from cloudflare_caller import batch_update, get_dns, get_zone_name
from constants import (CF_BASE_URL, DEFAULT_RUN_TIME_SECONDS, DOMAIN_FILE,
                       DOMAIN_PATTERN, IP_PATTERN, IP_URLS, SECONDS_PER_HOUR)
from logger import logger

load_dotenv()

API_TOKEN = getenv("API_TOKEN")
ZONE_ID = getenv("ZONE_ID")
RUN_EVERY = int(getenv("RUN_EVERY", DEFAULT_RUN_TIME_SECONDS))

CF_CLIENT = Client(api_token=API_TOKEN, base_url=CF_BASE_URL)

DNS_CACHE = {}
UNMATCHED_BLACKLIST = {}

LAST_NO_UPDATE_LOG_DATETIME = None


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
                f"Failed to get IP from {url}: {ip_response.status_code}"
            )
        except Exception as e:
            logger.warning(f"Failed to get ip from {url}, with exception {e}")

    return None


def get_config_domains(zone_name):
    global DNS_CACHE

    with open(DOMAIN_FILE) as f:
        config_domains = load(f)

    assert isinstance(
        config_domains, list
    ), "domains.json file did not contain a list"

    for domain in config_domains:
        assert isinstance(domain, str), f"domain {domain} is not a string"
        assert (
            fullmatch(DOMAIN_PATTERN, domain) is not None
        ), f"domain {domain} does not match subdomain regex pattern"

    domain_names = set(
        [
            f"{domain}.{zone_name}" if domain != "@" else f"{zone_name}"
            for domain in config_domains
        ]
    )

    DNS_CACHE = {
        domain: dns
        for domain, dns in DNS_CACHE.items()
        if domain in domain_names
    }

    return domain_names


def get_domains_to_update(config_domains, local_ip):
    domains_to_update = set()
    for domain in config_domains.difference(UNMATCHED_BLACKLIST.keys()):
        if domain not in DNS_CACHE:
            logger.info(f"Uncached domain {domain} found")
            domains_to_update.add(domain)
            continue
        if DNS_CACHE[domain].ip != local_ip:
            domains_to_update.add(domain)

    return domains_to_update


def clean_blacklist():
    global UNMATCHED_BLACKLIST

    UNMATCHED_BLACKLIST = {
        domain: blacklisted_on
        for domain, blacklisted_on in UNMATCHED_BLACKLIST.items()
        if (datetime.now() - blacklisted_on).days > 0
    }


def check(zone_name):
    global LAST_NO_UPDATE_LOG_DATETIME

    try:
        config_domains = get_config_domains(zone_name)
    except AssertionError as e:
        logger.error("Failed to load domains from json file: ", e)
        return None, None

    if len(config_domains) == 0:
        logger.warning("No domains in domains.jon file")
        return None, None

    local_ip = get_local_ip()
    if local_ip is None:
        logger.error("Could not get a local ip")
        return None, None

    domains_to_update = get_domains_to_update(config_domains, local_ip)

    if len(domains_to_update) == 0:
        if (
            LAST_NO_UPDATE_LOG_DATETIME is None
            or (datetime.now() - LAST_NO_UPDATE_LOG_DATETIME).seconds
            > SECONDS_PER_HOUR
        ):
            LAST_NO_UPDATE_LOG_DATETIME = datetime.now()
            logger.info(f"IP: {local_ip}. All DNS records match")
        return None, None

    logger.info(
        f"IP: {local_ip}. Need to update: {', '.join(domains_to_update)}"
    )

    cf_dns = get_dns(CF_CLIENT, ZONE_ID)
    if cf_dns is None:
        logger.error("Could not fetch Cloudflare domains")
        return None, None

    if len(cf_dns) == 0:
        logger.warning("No domains found in Cloudflare Zone")
        return None, None

    dns_to_update = []
    for domain in domains_to_update:
        if domain not in cf_dns.keys():
            UNMATCHED_BLACKLIST[domain] = datetime.now()
            logger.warning(
                f"Domain {domain} not found in zone. Blacklisting for 24hs"
            )
            continue
        if cf_dns[domain].ip == local_ip:
            DNS_CACHE[domain] = cf_dns[domain]
            logger.info(
                f"Domain {domain} already pointing to local IP {local_ip}"
            )
            continue
        dns_to_update.append(cf_dns[domain])

    return (dns_to_update, local_ip)


def update(dns_to_update, local_ip):
    for dns in dns_to_update:
        dns.ip = local_ip

    updated_dns = batch_update(CF_CLIENT, ZONE_ID, dns_to_update)

    if updated_dns is None:
        logger.warning(
            "Failed to update DNS records. Check previous messages for errors"
        )
        return

    for domain, dns in updated_dns.items():
        DNS_CACHE[domain] = dns
        logger.info(f"Updated {domain} to IP {dns.ip}")


def check_and_update(zone_name):
    dns_to_update, local_ip = check(zone_name)

    if dns_to_update is None or local_ip is None:
        return

    if len(dns_to_update) == 0:
        logger.info("Nothing left to update")
        return

    update(dns_to_update, local_ip)


def main():
    zone_name = get_zone_name(CF_CLIENT, ZONE_ID)

    if zone_name is None:
        logger.critical(
            f"Failed to find requested CF Zone {ZONE_ID}. Quitting."
        )
        return

    logger.info(f"Client set up and using zone: {zone_name}")
    logger.info(f"Updating DNS records now and every {RUN_EVERY} seconds")

    check_and_update(zone_name)

    schedule.every(RUN_EVERY).seconds.do(check_and_update, zone_name)
    schedule.every().day.do(clean_blacklist)
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
