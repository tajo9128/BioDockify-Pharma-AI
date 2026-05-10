"""
Knowledge Client Module
DEPRECATED: This module is maintained for backward compatibility.
Please use `modules.surfsense.client` instead.

All functionality has been consolidated into the main SurfSense client.
"""
import warnings
import logging

# Re-export from the main SurfSense client module
from modules.surfsense.client import (
    SurfSenseClient,
    get_surfsense_client,
    configure_surfsense
)

logger = logging.getLogger("knowledge.client")

# Deprecation warning on import
warnings.warn(
    "modules.knowledge.client is deprecated. Use modules.surfsense.client instead.",
    DeprecationWarning,
    stacklevel=2
)


# Legacy singleton for backward compatibility
# Maps to the main SurfSense client
surfsense = None


def _get_legacy_client():
    """Get legacy client (redirects to main SurfSense client)."""
    global surfsense
    if surfsense is None:
        surfsense = get_surfsense_client()
        logger.info("Initialized legacy SurfSense client (redirected to modules.surfsense.client)")
    return surfsense


# Initialize on module load for code that directly accesses `surfsense`
try:
    surfsense = get_surfsense_client()
except Exception:
    pass  # Will be initialized later


# Re-export factory function with deprecation
def get_client(base_url: str = "http://localhost:8000") -> SurfSenseClient:
    """
    DEPRECATED: Use modules.surfsense.client.get_surfsense_client() instead.
    """
    warnings.warn(
        "get_client() is deprecated. Use modules.surfsense.client.get_surfsense_client() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return get_surfsense_client(base_url=base_url)
