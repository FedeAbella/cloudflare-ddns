# Cloudflare Dynamic IP Updater

_A simple, to the point python script to update Cloudflare DNS records with a
dynamic IP. Also possible using Docker._

I recently set up my first homelab, using
[Cloudflare](https://www.cloudflare.com/) to reverse proxy into it from my own
domain. But having an ISP that only provides dynamic IPs, I needed some way to
update the IP in the DNS records. There's several solutions for this around, but
none that I found were completely to my liking, so I decided to make my own.

## Features

- Simple python script which does the bare minimum
- Lean Docker image when built, with no network or exposed ports needed
- Minimal `pip` requirements
- Uses Cloudflare's own
  [python library](https://github.com/cloudflare/cloudflare-python) to perform
  Cloudflare operations
- Uses the Cloudflare Batch API operation to update all DNS records in a single
  API call
- Only up to 2 API calls per update cycle: one to retrieve the DNS IPs, one to
  retrieve current DNS status, and one to perform updates (if needed)

## How to use

There's two ways of running this: as a python script, or using
[Docker](https://www.docker.com/). In both cases you'll need:

- A `.env` file which defines:
  - An `API_TOKEN` environment variable which contains
    [your Cloudflare API token](https://developers.cloudflare.com/fundamentals/api/get-started/create-token/)
  - A `ZONE_ID` environment variable which contains
    [your Cloudflare Zone ID](https://developers.cloudflare.com/fundamentals/setup/find-account-and-zone-ids/)
- A `domains.json` file which defines an array of DNS names to update:
  - Names should only contain the subdomain part (e.g.: if your zone is
    `mybestcfzone.org` and you want to update the `bestest` subdomain, only add
    `bestest` to the array)
  - The root DNS record can be added the same way as in the Cloudflare
    dashboard, by using `@` as the subdomain name

### As a Python script

1. Create a python `venv` and install the required packages using `pip` and the
   `requirements` file.

1. Put both the `.env` and `domains.json` file in the `src` directory (only the
   `domains.json` file really needs to be there, but for convenience sake), and
   run

   ```bash
   source .env && python updater.py
   ```

### Docker (recommended)

#### Build your own image

1. Make sure `docker` and `docker-compose`
   [are installed](https://docs.docker.com/desktop/setup/install/linux/)

1. Put both the `.env` and `domains.json` in the same directory as the
   `Dockerfile` and `docker-compose.yml` files and run

   ```bash
   docker compose up -d
   ```

#### Use dockerhub image

1. Copy the `docker-compose.yml` file to your desire location and change the
   line:

   ```yml
   build: .
   ```

   to

   ```yml
   image: fedeabella/cloudflare-ddns
   ```

1. Put both the `.env` and `domains.json` in the same directory as the
   `docker-compose.yml` file and run

   ```bash
   docker compose up -d
   ```

For either method, you can check the docker logs to see if the container is
running the script properly:

```bash
docker logs cloudflare-ddns
```

## Limitations

This was very much built in a couple afternoons to satisfy my personal needs, so
it may not have everything you need. For example:

- Only updates `A` records
- Only updates IP values in the records, no comments, proxiable values, etc.
- Only works on a single Cloudflare Zone
- Does not create new records, only updates existing ones

If you find something you need, feel free to create an Issue and I might look
into it, but no promises.
