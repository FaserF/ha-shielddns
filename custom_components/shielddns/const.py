"""Constants for the ShieldDNS integration."""

import logging

DOMAIN = "shielddns"
LOGGER = logging.getLogger(__package__)

CONF_HOST = "host"
CONF_PORT = "port"
CONF_TOKEN = "token"
CONF_USE_SSL = "use_ssl"
CONF_VERIFY_SSL = "verify_ssl"
CONF_UPDATE_INTERVAL = "update_interval"

DEFAULT_PORT = 443

DEFAULT_UPDATE_INTERVAL = 5
