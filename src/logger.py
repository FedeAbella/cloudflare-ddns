import logging

from constants import LOGGER_FORMAT

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
fh = logging.StreamHandler()
fh_formatter = logging.Formatter(LOGGER_FORMAT)
fh.setFormatter(fh_formatter)
logger.addHandler(fh)
