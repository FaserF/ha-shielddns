"""Constants for the ShieldDNS integration."""

import logging

DOMAIN = "shielddns"
LOGGER = logging.getLogger(__package__)

CONF_HOST = "host"
CONF_PORT = "port"
CONF_TOKEN = "token"
CONF_USE_SSL = "use_ssl"
CONF_VERIFY_SSL = "verify_ssl"

DEFAULT_PORT = 443

UPDATE_INTERVAL = 30
