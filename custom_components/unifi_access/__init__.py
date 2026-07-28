"""The Unifi Access integration."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import ssl

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.util import ssl as ssl_util
from unifi_access_api import ApiConnectionError, EmergencyStatus, UnifiAccessApiClient

from .const import DOMAIN, STORAGE_KEY, STORAGE_VERSION
from .coordinator import UnifiAccessCoordinator
from .frontend import async_register_card
from .guest_pass import GuestPassManager
from .hub import DoorState, UnifiAccessHub
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.COVER,
    Platform.EVENT,
    Platform.IMAGE,
    Platform.LOCK,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


@dataclass
class UnifiAccessData:
    """Runtime data for the Unifi Access integration."""

    hub: UnifiAccessHub
    coordinator: UnifiAccessCoordinator[dict[str, DoorState]]
    emergency_coordinator: UnifiAccessCoordinator[EmergencyStatus]
    guest_passes: GuestPassManager
    store: Store


type UnifiAccessConfigEntry = ConfigEntry[UnifiAccessData]


async def async_setup_entry(hass: HomeAssistant, entry: UnifiAccessConfigEntry) -> bool:
    """Set up Unifi Access from a config entry."""
    session = async_get_clientsession(hass, verify_ssl=entry.data["verify_ssl"])

    ssl_context: ssl.SSLContext | bool = False
    if entry.data["verify_ssl"]:
        # SSL context creation may call into blocking cert-loading functions.
        ssl_context = await hass.async_add_executor_job(ssl_util.client_context)

    client_kwargs = {
        "host": entry.data["host"],
        "api_token": entry.data["api_token"],
        "session": session,
        "verify_ssl": entry.data["verify_ssl"],
        "ssl_context": ssl_context,
    }

    client = UnifiAccessApiClient(**client_kwargs)

    hub = UnifiAccessHub(
        client,
        use_polling=entry.data["use_polling"],
        session=session,
        host=entry.data["host"],
        api_token=entry.data["api_token"],
        verify_ssl=entry.data["verify_ssl"],
        ssl_context=ssl_context,
    )

    try:
        await hub.client.authenticate()
    except ApiConnectionError as err:
        raise ConfigEntryNotReady("Unable to connect to UniFi Access") from err

    coordinator: UnifiAccessCoordinator[dict[str, DoorState]] = UnifiAccessCoordinator(
        hass,
        entry,
        hub,
        name="Unifi Access Coordinator",
        update_method=hub.async_update,
        always_update=True,
    )
    await coordinator.async_config_entry_first_refresh()

    emergency_coordinator: UnifiAccessCoordinator[EmergencyStatus] = (
        UnifiAccessCoordinator(
            hass,
            entry,
            hub,
            name="Unifi Access Emergency Coordinator",
            update_method=hub.async_get_emergency_status,
        )
    )
    await emergency_coordinator.async_config_entry_first_refresh()

    # Discover access readers and fetch their access-method settings
    # (non-fatal if the API calls fail). Also maps each door's hub type/id.
    try:
        await hub.async_fetch_devices()
        await hub.async_refresh_all_readers()
    except Exception as err:
        _LOGGER.warning("Reader discovery failed: %s", err)

    # Restore persisted per-door entity types (e.g. garage/gate for UGT doors).
    store: Store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    stored_types = await store.async_load() or {}
    # Migrate the old format: {"entity_types": {"door_id": "value"}}.
    if "entity_types" in stored_types:
        stored_types = stored_types["entity_types"]
    for door_id, door_state in coordinator.data.items():
        if door_id in stored_types:
            door_state.entity_type = stored_types[door_id]

    # Wire WebSocket push → coordinator updates
    hub.on_doors_updated = lambda: coordinator.async_set_updated_data(hub.doors)
    hub.on_emergency_updated = lambda: emergency_coordinator.async_set_updated_data(
        EmergencyStatus(evacuation=hub.evacuation, lockdown=hub.lockdown)
    )

    guest_passes = GuestPassManager(hass, hub, entry.entry_id)
    await guest_passes.async_load()
    # Hook into per-door last_access events so the manager can stamp
    # arrived_at instantly when a guest uses their credential — without
    # waiting for the next list_guest_passes poll.
    guest_passes.async_start(hub.doors.values())

    entry.runtime_data = UnifiAccessData(
        hub=hub,
        coordinator=coordinator,
        emergency_coordinator=emergency_coordinator,
        guest_passes=guest_passes,
        store=store,
    )

    async_setup_services(hass)

    # Auto-register the bundled Lovelace card (non-fatal if it fails).
    try:
        await async_register_card(hass)
    except Exception as err:
        _LOGGER.warning("Guest-pass card registration failed: %s", err)

    hub.create_task = lambda coro: entry.async_create_background_task(
        hass, coro, "unifi_access_background_task"
    )

    if not hub.use_polling:
        hub.start_websocket()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: UnifiAccessConfigEntry
) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        entry.runtime_data.guest_passes.async_stop()
        await entry.runtime_data.hub.async_close()
        if len(hass.config_entries.async_entries(DOMAIN)) <= 1:
            async_unload_services(hass)

    return unload_ok


async def async_remove_config_entry_device(
    hass: HomeAssistant,
    config_entry: UnifiAccessConfigEntry,
    device_entry: dr.DeviceEntry,
) -> bool:
    """Allow removal of devices that are no longer present."""
    hub = config_entry.runtime_data.hub
    return not any(
        identifier
        for identifier in device_entry.identifiers
        if identifier[0] == DOMAIN and identifier[1] in hub.doors
    )
