"""Frontend registration for the Unifi Access Lovelace cards.

The guest-pass and last-access cards ship inside the integration. They are
registered as Lovelace module resources so the dashboard reliably loads them
before rendering (a plain `add_extra_js_url` can race the dashboard render).
YAML-mode dashboards, where resources cannot be created programmatically, fall
back to `add_extra_js_url`.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

_CARD_FILENAMES = (
    "unifi_access_guest_card.js",
    "unifi_access_last_access_card.js",
)
_REGISTERED_KEY = f"{DOMAIN}_card_registered"


async def async_register_card(hass: HomeAssistant) -> None:
    """Serve the bundled Lovelace cards and register them for the frontend."""
    if hass.data.get(_REGISTERED_KEY):
        return
    hass.data[_REGISTERED_KEY] = True

    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                f"/{DOMAIN}/{filename}",
                hass.config.path(f"custom_components/{DOMAIN}/{filename}"),
                False,
            )
            for filename in _CARD_FILENAMES
        ]
    )

    integration = await async_get_integration(hass, DOMAIN)
    for filename in _CARD_FILENAMES:
        # Cache-bust the resource URL on the file content hash and the
        # integration version, so the URL changes when the file content does.
        path = Path(hass.config.path(f"custom_components/{DOMAIN}/{filename}"))
        token = await hass.async_add_executor_job(_safe_content_token, path)
        url = f"/{DOMAIN}/{filename}?v={integration.version}.{token}"
        await _async_register_resource(hass, url)


def _safe_content_token(path: Path) -> str:
    """Return a short content hash of the file for cache-busting.

    The hash changes exactly when the file's bytes change. Falls back to the
    mtime, then ``"0"``, if the file can't be read.
    """
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    except OSError:
        try:
            return str(int(path.stat().st_mtime))
        except OSError:
            return "0"


async def _async_register_resource(hass: HomeAssistant, url: str) -> None:
    """Register the card as a Lovelace module resource (race-free)."""
    lovelace_data = hass.data.get("lovelace")
    resources = getattr(lovelace_data, "resources", None)

    # YAML-mode dashboards expose no mutable resource collection — fall back.
    if resources is None or not hasattr(resources, "async_create_item"):
        frontend.add_extra_js_url(hass, url)
        return

    try:
        if not resources.loaded:
            await resources.async_load()
            resources.loaded = True

        base = url.split("?", maxsplit=1)[0]
        for item in resources.async_items():
            existing = str(item.get("url", ""))
            if existing.split("?", maxsplit=1)[0] != base:
                continue
            if existing == url:
                return  # already registered with the current cache-buster
            # Same card, stale cache-buster — update it in place so the
            # browser fetches the new file.
            await resources.async_update_item(
                item["id"], {"res_type": "module", "url": url}
            )
            return

        await resources.async_create_item({"res_type": "module", "url": url})
    except Exception as err:  # registration is non-fatal
        _LOGGER.warning(
            "Could not register %s as a Lovelace resource "
            "(%s); falling back to extra_js_url",
            url,
            err,
        )
        frontend.add_extra_js_url(hass, url)
