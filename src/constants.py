# App config
DEFAULT_RUN_TIME_SECONDS = "60"
LOGGER_FORMAT = "%(asctime)s :: %(levelname)s :: %(message)s"

# App data
DOMAIN_FILE = "./config/domains.json"

# URLs
CF_BASE_URL = "https://api.cloudflare.com/client/v4"
IP_URLS = [
    "https://icanhazip.com",
    "https://api.ipify.org",
    "https://ipinfo.io/ip",
    "https://ipecho.net/plain",
    "https://ifconfig.me/ip",
]

# Regex patterns
DOMAIN_PATTERN = r"@|[a-z0-9]([a-z0-9-].*[a-z0-9])?"
IP_PATTERN = r"(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)){3}"

# Misc
SECONDS_PER_HOUR = 3600
