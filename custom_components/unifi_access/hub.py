"""Unifi Access Hub.

Manages door state, websocket event handling, and update notifications
for the Home Assistant integration.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import UTC, datetime
import logging
import ssl
import time
from typing import TYPE_CHECKING, Any
import unicodedata

import aiohttp
from unifi_access_api import (
    ApiError,
    ApiNotFoundError,
    BaseInfo,
    DeviceUpdate,
    Door,
    DoorLockRelayStatus,
    DoorLockRule,
    DoorLockRuleType,
    DoorPositionStatus,
    EmergencyStatus,
    HwDoorbell,
    InsightsAdd,
    LocationUpdateLegacy,
    LocationUpdateV2,
    LogAdd,
    RemoteUnlock,
    RemoteView,
    RemoteViewChange,
    SettingUpdate,
    UnifiAccessApiClient,
    V2DeviceUpdate,
    V2LocationUpdate,
    WsMessageHandler,
)
from unifi_access_api.models.websocket import WebsocketMessage

from .const import (
    ACCESS_ENTRY_EVENT,
    ACCESS_EXIT_EVENT,
    ACCESS_GENERIC_EVENT,
    ACCESS_METHOD_CAPABILITY_TOKENS,
    ANTI_SPOOFING_OPTION_BY_PAIR,
    DOOR_TYPE_LOCK,
    DOORBELL_START_EVENT,
    DOORBELL_STOP_EVENT,
)

if TYPE_CHECKING:
    from .capture import CaptureStore

_LOGGER = logging.getLogger(__name__)


def _normalize_name(name: str) -> str:
    """Normalize a door name using NFC normalization."""
    if not name:
        return ""
    return unicodedata.normalize("NFC", name.strip())


EventListener = Callable[[str, dict[str, str]], None]


@dataclass
class DoorState:
    """Mutable runtime state for a single door."""

    door: Door
    hub_id: str | None = None
    hub_type: str | None = None
    # HA entity type (lock / garage / gate); selectable for UGT doors.
    entity_type: str = DOOR_TYPE_LOCK
    lock_rule: str = ""
    lock_rule_ended_time: int = 0
    lock_rule_interval: int = 10
    # Cover (garage/gate) travel timing + obstruction flag.
    open_time: int = 0
    close_time: int = 0
    obstruction_detected: bool = False
    doorbell_request_id: str | None = None
    thumbnail: bytes | None = None
    thumbnail_last_updated: datetime | None = None

    _event_listeners: dict[str, list[EventListener]] = field(
        default_factory=dict, repr=False
    )

    @property
    def id(self) -> str:
        """Return the door id."""
        return str(self.door.id)

    @property
    def name(self) -> str:
        """Return the door name."""
        return str(self.door.name)

    @property
    def door_position_status(self) -> DoorPositionStatus:
        """Return the door position status."""
        return self.door.door_position_status

    @property
    def door_lock_relay_status(self) -> DoorLockRelayStatus:
        """Return the door lock relay status."""
        return self.door.door_lock_relay_status

    @property
    def is_locked(self) -> bool:
        """Return whether the door is locked."""
        return bool(self.door.door_lock_relay_status == DoorLockRelayStatus.LOCK)

    @property
    def is_open(self) -> bool:
        """Return whether the door is open."""
        return bool(self.door.door_position_status == DoorPositionStatus.OPEN)

    @property
    def doorbell_pressed(self) -> bool:
        """Return whether the doorbell is currently pressed."""
        return self.doorbell_request_id is not None

    def add_event_listener(self, event: str, listener: EventListener) -> None:
        """Add an event listener."""
        self._event_listeners.setdefault(event, []).append(listener)

    def remove_event_listener(self, event: str, listener: EventListener) -> None:
        """Remove an event listener."""
        listeners = self._event_listeners.get(event)
        if listeners and listener in listeners:
            listeners.remove(listener)

    def trigger_event(self, event: str, attributes: dict[str, str]) -> None:
        """Trigger all listeners for a given event."""
        for listener in self._event_listeners.get(event, []):
            listener(event, attributes)


_FACE_UNLOCK_CAPABILITIES = frozenset({"support_face", "identity_face_unlock"})
# Capabilities that identify an access reader (intercom / reader). Only readers
# host access methods — the door hub does not.
_READER_CAPABILITIES = frozenset({"is_reader", "identity_is_reader"})
# Capabilities that identify a hub / controller (UAH, UGT, …). Used to map a
# door's hub type/id at setup instead of waiting for a WS device update.
_HUB_CAPABILITIES = frozenset({"is_hub", "identity_is_hub"})

# Time window (seconds) for collapsing the same physical access arriving via
# both insights.add and logs.add.
_ACCESS_DEDUP_WINDOW = 3.0

# Time window (seconds) in which a door thumbnail published after an access or
# doorbell ring is stored as that event's capture image.
_CAPTURE_WINDOW = 15.0

# Time window (seconds) for the reverse order: a thumbnail that arrived just
# before its event is claimed retroactively. The controller publishes the
# snapshot and the access record on independent paths, so a denied access
# often reaches the integration after its own snapshot.
_CAPTURE_BACKFILL_WINDOW = 10.0


@dataclass
class ReaderState:
    """Mutable runtime state for a single access reader (intercom / reader)."""

    device_id: str
    door_id: str
    info: dict  # raw device dict from /api/v1/developer/devices
    access_methods: dict | None = None
    # Sticky anti-spoofing combo (option key from ANTI_SPOOFING_COMBOS): the
    # last value seen while face unlock was enabled, or the last explicit
    # selection. Kept stable when face unlock is off (UniFi reports a default).
    last_anti_spoofing_combo: str | None = None

    @property
    def capabilities(self) -> list[str]:
        """Return the reader's capability strings."""
        return self.info.get("capabilities") or []

    @property
    def alias(self) -> str:
        """Return the reader alias (falls back to name / id)."""
        return self.info.get("alias") or self.info.get("name") or self.device_id

    @property
    def model(self) -> str | None:
        """Return the reader model / device type."""
        return self.info.get("type")

    @property
    def name(self) -> str:
        """Return the HA device name (alias + model)."""
        model = self.model
        return f"{self.alias} ({model})" if model else self.alias

    @property
    def supports_face(self) -> bool:
        """Return whether the reader hardware supports face unlock."""
        return bool(set(self.capabilities) & _FACE_UNLOCK_CAPABILITIES)

    def supports_method(self, method: str) -> bool:
        """Return whether the reader hardware supports an access method.

        The settings endpoint reports some methods even when the hardware
        cannot use them; the capability array is authoritative. If the device
        exposes no capabilities, or the method is unmapped, no filtering is
        applied.
        """
        capabilities = self.capabilities
        if not capabilities:
            return True
        tokens = ACCESS_METHOD_CAPABILITY_TOKENS.get(method)
        if not tokens:
            return True
        return any(
            token in capability for token in tokens for capability in capabilities
        )


class UnifiAccessHub:
    """Manages door state and websocket events on top of the async API client."""

    def __init__(
        self,
        client: UnifiAccessApiClient,
        *,
        use_polling: bool = False,
        session: aiohttp.ClientSession | None = None,
        host: str = "",
        api_token: str = "",
        verify_ssl: bool = False,
        ssl_context: ssl.SSLContext | bool = False,
    ) -> None:
        """Initialize the hub."""
        self.client = client
        self.use_polling = use_polling
        self.doors: dict[str, DoorState] = {}
        self.evacuation: bool = False
        self.lockdown: bool = False
        self.supports_door_lock_rules: bool = True

        # Access reader support (intercoms / readers and their access methods).
        self._session = session
        self._host = host
        self._api_token = api_token
        self._ssl_context: ssl.SSLContext | bool = ssl_context
        self.devices: dict[str, dict] = {}  # device_id → raw device data
        self.readers: dict[str, ReaderState] = {}  # device_id → reader state

        # Callbacks registered by switch/select platforms to add reader
        # entities once a reader's access-method settings are first known.
        # _discovered_readers is a permanent record so late-registering
        # platforms still get notified of earlier discoveries.
        self._reader_callbacks: list[Callable[[str], None]] = []
        self._discovered_readers: set[str] = set()

        # Dedup: track last insights.add timestamp per door to suppress
        # redundant logs.add events when a hub sends both.
        self._last_insight_time: dict[str, float] = {}

        # Dedup state for the "access" and "last_access" events: canonical
        # door id → (monotonic ts, signature). The same physical access can
        # arrive via both insights.add and logs.add. Separate dicts are used
        # because both events fire in the same handler.
        self._access_event_dedup: dict[str, tuple[float, str]] = {}
        self._last_access_dedup: dict[str, tuple[float, str]] = {}

        # Cached index from any WS-reported door identifier (door UUID, bound
        # hub id, or reader device id) to the canonical door id. Populated on
        # first resolution; a cached entry for a removed door is re-resolved.
        self._door_id_index: dict[str, str] = {}

        # device id (MAC) → door UUID, built from the raw /devices list in
        # ``async_fetch_devices``. An extra resolution class for WS access
        # events that report a device/hub MAC instead of the door UUID.
        self._device_door_map: dict[str, str] = {}

        # Capture images: door id → (capture id, monotonic ts) awaiting the
        # thumbnail that the controller publishes shortly after the event.
        self._pending_capture: dict[str, tuple[str, float]] = {}

        # Reverse direction: door id → (image, monotonic ts) of the most recent
        # thumbnail that no event had claimed yet.
        self._recent_thumbnail: dict[str, tuple[bytes, float]] = {}

        # Set by __init__.py — shared store holding the capture images.
        self.captures: CaptureStore | None = None

        # Set by __init__.py after coordinator creation to push WS updates.
        self.on_doors_updated: Callable[[], None] | None = None
        self.on_emergency_updated: Callable[[], None] | None = None
        self.create_task: Callable[[Coroutine[Any, Any, None]], Any] | None = None

    def _notify_doors_updated(self) -> None:
        """Notify that door state changed (triggers coordinator update)."""
        if self.on_doors_updated:
            self.on_doors_updated()

    def _notify_emergency_updated(self) -> None:
        """Notify that emergency state changed (triggers coordinator update)."""
        if self.on_emergency_updated:
            self.on_emergency_updated()

    def _notify_reader_ready(self, device_id: str) -> None:
        """Notify (once) that a reader's access methods have been fetched."""
        if device_id in self._discovered_readers:
            return
        self._discovered_readers.add(device_id)
        for cb in self._reader_callbacks:
            cb(device_id)

    def register_reader_callback(self, callback: Callable[[str], None]) -> None:
        """Register a callback fired once a reader's settings are first known.

        Called immediately for every reader already discovered so
        late-registering platforms don't miss earlier discoveries.
        """
        self._reader_callbacks.append(callback)
        for device_id in self._discovered_readers:
            callback(device_id)

    # ------------------------------------------------------------------
    # Device API helpers
    # ------------------------------------------------------------------

    def _device_api_url(self, path: str) -> str:
        """Build a full URL for the device API."""
        host = self._host
        if ":" not in host:
            host = f"{host}:12445"
        return f"https://{host}{path}"

    def _api_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_token}"}

    async def async_fetch_devices(self) -> dict[str, ReaderState]:
        """Fetch all devices and build reader states linked to their doors.

        A device is treated as a reader (and gets access-method entities) when
        it exposes a reader capability and its ``location_id`` matches a known
        door. The door hub itself is skipped.
        """
        if self._session is None:
            _LOGGER.warning("unifi_access: async_fetch_devices — no HTTP session")
            return {}
        url = self._device_api_url("/api/v1/developer/devices")
        _LOGGER.debug("unifi_access: fetching devices from %s", url)
        try:
            async with self._session.get(
                url, headers=self._api_headers(), ssl=self._ssl_context
            ) as resp:
                data = await resp.json()
        except Exception as err:
            _LOGGER.warning("unifi_access: failed to fetch devices: %s", err)
            return {}

        if data.get("code") != "SUCCESS":
            _LOGGER.warning(
                "unifi_access: device list returned code=%s", data.get("code")
            )
            return {}

        for device in self._flatten_device_list(data.get("data", [])):
            self._register_device(device)

        self._map_hub_types()
        _LOGGER.debug("unifi_access: %d reader(s) discovered", len(self.readers))
        return self.readers

    def _map_hub_types(self) -> None:
        """Map each door's hub type/id from the raw device list.

        Runs once after device discovery so ``door.hub_type`` (used as the HA
        device model and to detect UGT gate hubs) is known at setup instead of
        only after a later WS device update. Also builds ``_device_door_map``
        (device MAC → door UUID) used as an extra WS door-resolution class.

        Only fills a door whose ``hub_id`` is still unset, so a value already
        learned from a WS event is never overwritten.
        """
        hub_types: dict[str, str | None] = {}
        for dev in self.devices.values():
            dev_id = dev.get("id")
            if dev_id and set(dev.get("capabilities") or []) & _HUB_CAPABILITIES:
                hub_types[dev_id] = dev.get("type")

        for dev in self.devices.values():
            location_id = dev.get("location_id")
            if not location_id or location_id not in self.doors:
                continue
            # device MAC → door map (all devices on a known door)
            dev_id = dev.get("id")
            if dev_id:
                self._device_door_map[dev_id] = location_id

            state = self.doors[location_id]
            if state.hub_id is not None:
                continue
            capabilities = set(dev.get("capabilities") or [])
            if capabilities & _HUB_CAPABILITIES:
                state.hub_type = dev.get("type")
                state.hub_id = dev.get("id")
            elif dev.get("connected_uah_id") in hub_types:
                connected_id = dev["connected_uah_id"]
                state.hub_type = hub_types[connected_id]
                state.hub_id = connected_id

    @staticmethod
    def _flatten_device_list(raw: list) -> list[dict]:
        """Flatten the device list.

        The API wraps devices in an outer list with one inner list per door /
        console: ``[[dev, dev], [dev, dev], ...]``. Every inner list must be
        flattened so multi-door sites are fully discovered (not just the first
        group). A flat list of device dicts is also accepted.
        """
        devices: list[dict] = []
        for entry in raw:
            if isinstance(entry, list):
                devices.extend(d for d in entry if isinstance(d, dict))
            elif isinstance(entry, dict):
                devices.append(entry)
        return devices

    def _register_device(self, device: dict) -> None:
        """Cache a device; if it is a reader on a known door, register it.

        Only readers (intercoms / readers) host access methods — the door hub
        is skipped. A reader is linked to its door via ``location_id`` == door id.
        """
        device_id = device.get("id")
        if not device_id:
            return
        self.devices[device_id] = device

        capabilities = set(device.get("capabilities") or [])
        if not capabilities & _READER_CAPABILITIES:
            return  # not a reader (e.g. the door hub) → no access methods

        door_id = device.get("location_id")
        if not door_id or door_id not in self.doors:
            _LOGGER.debug(
                "unifi_access: reader %s has no matching door (location_id=%s)",
                device_id,
                door_id,
            )
            return

        if device_id in self.readers:
            # Keep the raw info fresh (capabilities / alias may change).
            self.readers[device_id].info = device
        else:
            self.readers[device_id] = ReaderState(
                device_id=device_id, door_id=door_id, info=device
            )
            _LOGGER.debug(
                "unifi_access: discovered reader %s (%s) on door %s",
                device.get("alias") or device.get("name"),
                device_id,
                door_id,
            )

    async def async_refresh_all_readers(self) -> None:
        """Fetch access-method settings for every discovered reader."""
        for device_id in list(self.readers):
            await self.async_refresh_reader_settings(device_id)

    async def async_refresh_reader_settings(self, device_id: str) -> None:
        """Fetch a reader's access-method settings and update its state."""
        reader = self.readers.get(device_id)
        if reader is None:
            return
        if self._session is None:
            _LOGGER.warning(
                "unifi_access: no HTTP session for reader %s settings", device_id
            )
            return
        url = self._device_api_url(f"/api/v1/developer/devices/{device_id}/settings")
        try:
            async with self._session.get(
                url, headers=self._api_headers(), ssl=self._ssl_context
            ) as resp:
                data = await resp.json()
        except Exception as err:
            _LOGGER.warning(
                "unifi_access: failed to fetch settings for reader %s: %s",
                device_id,
                err,
            )
            return

        if data.get("code") != "SUCCESS":
            _LOGGER.warning(
                "unifi_access: settings fetch for reader %s returned code=%s",
                device_id,
                data.get("code"),
            )
            return

        raw = data.get("data")
        if isinstance(raw, list):
            raw = raw[0] if raw else {}
        if not isinstance(raw, dict):
            _LOGGER.warning(
                "unifi_access: unexpected settings data for reader %s: %s",
                device_id,
                data,
            )
            return

        access_methods = raw.get("access_methods") or raw.get("settings", {}).get(
            "access_methods"
        )
        if access_methods is None:
            _LOGGER.warning(
                "unifi_access: no access_methods in settings for reader %s: %s",
                device_id,
                raw,
            )
            return
        reader.access_methods = access_methods
        _LOGGER.debug(
            "unifi_access: reader %s (%s) access_methods: %s",
            reader.alias,
            device_id,
            access_methods,
        )

        # Sticky anti-spoofing combo: adopt from a fetch only while face unlock
        # is enabled; when disabled UniFi reports a default, so keep the last.
        face = access_methods.get("face", {})
        combo = ANTI_SPOOFING_OPTION_BY_PAIR.get(
            (face.get("anti_spoofing_level"), face.get("detect_distance"))
        )
        if combo and (
            face.get("enabled") == "yes" or reader.last_anti_spoofing_combo is None
        ):
            reader.last_anti_spoofing_combo = combo

        self._notify_reader_ready(device_id)
        self._notify_doors_updated()

    async def async_update_reader_settings(self, device_id: str, payload: dict) -> None:
        """Write access-method settings for a reader."""
        if device_id not in self.readers:
            raise RuntimeError(f"Unknown reader {device_id}")
        if self._session is None:
            raise RuntimeError("No HTTP session available")
        url = self._device_api_url(f"/api/v1/developer/devices/{device_id}/settings")
        try:
            async with self._session.put(
                url,
                headers={
                    **self._api_headers(),
                    "Content-Type": "application/json",
                },
                json=payload,
                ssl=self._ssl_context,
            ) as resp:
                data = await resp.json()
        except Exception as err:
            raise RuntimeError(
                f"Failed to update settings for reader {device_id}"
            ) from err

        if data.get("code") != "SUCCESS":
            raise RuntimeError(
                f"Reader settings update failed: {data.get('msg') or data.get('code')}"
            )

    # ------------------------------------------------------------------
    # Visitor / guest-pass API (developer API, direct aiohttp)
    # ------------------------------------------------------------------

    async def _developer_api(
        self,
        method: str,
        path: str,
        *,
        json_body: dict | None = None,
        params: dict[str, str] | None = None,
    ) -> dict:
        """Call the UniFi Access developer API and return the parsed JSON.

        Raises RuntimeError on a transport error or a non-SUCCESS response.
        """
        if self._session is None:
            raise RuntimeError("No HTTP session available")
        headers = self._api_headers()
        if json_body is not None:
            headers["Content-Type"] = "application/json"
        try:
            async with self._session.request(
                method,
                self._device_api_url(path),
                headers=headers,
                json=json_body,
                params=params,
                ssl=self._ssl_context,
            ) as resp:
                data = await resp.json()
        except Exception as err:
            raise RuntimeError(f"{method} {path} failed: {err}") from err
        if data.get("code") != "SUCCESS":
            raise RuntimeError(
                f"{method} {path}: {data.get('msg') or data.get('code')}"
            )
        return data

    async def async_generate_pin(self) -> str:
        """Generate a fresh PIN code.

        The plaintext PIN is only obtainable here — a later visitor fetch
        returns just a hashed token.
        """
        data = await self._developer_api(
            "POST", "/api/v1/developer/credentials/pin_codes"
        )
        pin = data.get("data")
        if not isinstance(pin, str) or not pin:
            raise RuntimeError("PIN generation returned no code")
        return pin

    async def async_create_visitor(
        self,
        *,
        first_name: str,
        last_name: str,
        start_time: int,
        end_time: int,
        door_ids: list[str],
        visit_reason: str = "Others",
    ) -> dict:
        """Create a one-time visitor for one or more doors.

        Returns the visitor object.
        """
        if not door_ids:
            raise RuntimeError("At least one door is required")
        payload = {
            "first_name": first_name,
            "last_name": last_name,
            "start_time": int(start_time),
            "end_time": int(end_time),
            "visit_reason": visit_reason,
            "resources": [{"id": door_id, "type": "door"} for door_id in door_ids],
        }
        data = await self._developer_api(
            "POST", "/api/v1/developer/visitors", json_body=payload
        )
        visitor = data.get("data")
        if not isinstance(visitor, dict) or not visitor.get("id"):
            raise RuntimeError("Visitor creation returned no visitor id")
        return visitor

    async def async_assign_visitor_pin(self, visitor_id: str, pin: str) -> None:
        """Assign a generated PIN code to a visitor."""
        await self._developer_api(
            "PUT",
            f"/api/v1/developer/visitors/{visitor_id}/pin_codes",
            json_body={"pin_code": pin},
        )

    async def async_assign_visitor_qr(self, visitor_id: str) -> None:
        """Assign a QR code to a visitor (UniFi Access 3.3.10+)."""
        await self._developer_api(
            "PUT", f"/api/v1/developer/visitors/{visitor_id}/qr_codes"
        )

    async def async_update_visitor_window(
        self, visitor_id: str, start_time: int, end_time: int
    ) -> dict:
        """Update a visitor's validity window (reactivate / extend)."""
        data = await self._developer_api(
            "PUT",
            f"/api/v1/developer/visitors/{visitor_id}",
            json_body={
                "start_time": int(start_time),
                "end_time": int(end_time),
            },
        )
        return data.get("data") or {}

    async def async_cancel_visitor(self, visitor_id: str) -> None:
        """Cancel a visitor (soft delete — UniFi sets the status to CANCELLED)."""
        await self._developer_api("DELETE", f"/api/v1/developer/visitors/{visitor_id}")

    async def async_delete_visitor(self, visitor_id: str) -> None:
        """Permanently remove a visitor from UniFi Access."""
        await self._developer_api(
            "DELETE",
            f"/api/v1/developer/visitors/{visitor_id}",
            params={"is_force": "true"},
        )

    async def async_get_visitor(self, visitor_id: str) -> dict | None:
        """Fetch a visitor. Returns None if it no longer exists in UniFi."""
        try:
            data = await self._developer_api(
                "GET", f"/api/v1/developer/visitors/{visitor_id}"
            )
        except RuntimeError as err:
            if "not found" in str(err).lower():
                return None
            raise
        visitor = data.get("data")
        return visitor if isinstance(visitor, dict) else None

    async def async_download_visitor_qr(self, visitor_id: str) -> bytes:
        """Download a visitor's QR code as PNG image bytes."""
        if self._session is None:
            raise RuntimeError("No HTTP session available")
        path = f"/api/v1/developer/credentials/qr_codes/download/{visitor_id}"
        try:
            async with self._session.get(
                self._device_api_url(path),
                headers=self._api_headers(),
                ssl=self._ssl_context,
            ) as resp:
                content = await resp.read()
        except Exception as err:
            raise RuntimeError(
                f"QR download for visitor {visitor_id} failed: {err}"
            ) from err
        if content[:4] != b"\x89PNG":
            raise RuntimeError(
                f"QR download for visitor {visitor_id} did not return a PNG image"
            )
        return content

    async def async_trigger_doorbell(
        self,
        device_id: str,
        *,
        room_name: str | None = None,
        cancel: bool = False,
    ) -> None:
        """Ring the doorbell on an intercom or reader (UniFi Access 4.0.10+).

        ``room_name`` targets a specific entry of an intercom's directory;
        ``cancel`` stops a doorbell that is still ringing.
        """
        payload: dict[str, Any] = {"cancel": cancel}
        if room_name:
            payload["room_name"] = room_name
        await self._developer_api(
            "POST",
            f"/api/v1/developer/devices/{device_id}/doorbell",
            json_body=payload,
        )

    def doorbell_devices_for_door(self, door_id: str) -> list[ReaderState]:
        """Return the readers of a door, intercoms first."""
        readers = [r for r in self.readers.values() if r.door_id == door_id]
        readers.sort(key=lambda r: "intercom" not in str(r.model or "").lower())
        return readers

    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------

    async def async_update(self) -> dict[str, DoorState]:
        """Fetch all doors and return the door state dict (for coordinator)."""
        api_doors = await self.client.get_doors()
        for api_door in api_doors:
            if api_door.id in self.doors:
                self.doors[api_door.id].door = api_door
            else:
                self.doors[api_door.id] = DoorState(door=api_door)
        # Fetch lock rules for each door
        for door_id, state in self.doors.items():
            try:
                rule_status = await self.client.get_door_lock_rule(door_id)
                state.lock_rule = rule_status.type.value
                state.lock_rule_ended_time = rule_status.ended_time
            except ApiNotFoundError:
                _LOGGER.debug("Door lock rules not supported for door %s", door_id)
                self.supports_door_lock_rules = False
                break
        return self.doors

    async def async_get_emergency_status(self) -> EmergencyStatus:
        """Fetch the current emergency status."""
        status = await self.client.get_emergency_status()
        self.evacuation = status.evacuation
        self.lockdown = status.lockdown
        return status

    async def async_set_emergency_status(
        self, *, evacuation: bool | None = None, lockdown: bool | None = None
    ) -> None:
        """Set the emergency status."""
        current = await self.client.get_emergency_status()
        new_status = EmergencyStatus(
            evacuation=evacuation if evacuation is not None else current.evacuation,
            lockdown=lockdown if lockdown is not None else current.lockdown,
        )
        await self.client.set_emergency_status(new_status)
        self.evacuation = new_status.evacuation
        self.lockdown = new_status.lockdown
        self._notify_emergency_updated()

    async def async_set_lock_rule(self, door_id: str, rule_type: str) -> None:
        """Set a door lock rule."""
        if not rule_type:
            return

        state = self.doors.get(door_id)
        interval = state.lock_rule_interval if state else 0

        try:
            door_lock_rule_type = DoorLockRuleType(rule_type)
        except ValueError:
            _LOGGER.warning(
                "Unsupported door lock rule type '%s' for door %s",
                rule_type,
                door_id,
            )
            return

        rule = DoorLockRule(type=door_lock_rule_type, interval=interval)
        await self.client.set_door_lock_rule(door_id, rule)

        if state is not None:
            state.lock_rule = rule_type
            self._notify_doors_updated()

    # ------------------------------------------------------------------
    # WebSocket
    # ------------------------------------------------------------------

    def start_websocket(
        self,
        on_connect: Callable[[], Any] | None = None,
        on_disconnect: Callable[[], Any] | None = None,
    ) -> None:
        """Start the websocket connection with all event handlers."""
        handlers: dict[str, WsMessageHandler] = {
            "access.data.device.location_update_v2": self._handle_location_update,
            "access.data.v2.location.update": self._handle_v2_location_update,
            "access.data.location.update": self._handle_location_update_legacy,
            "access.data.v2.device.update": self._handle_v2_device_update,
            "access.logs.insights.add": self._handle_insights_add,
            "access.base.info": self._handle_base_info,
            "access.remote_view": self._handle_remote_view,
            "access.remote_view.change": self._handle_remote_view_change,
            "access.data.device.update": self._handle_device_update,
            "access.logs.add": self._handle_logs_add,
            "access.hw.door_bell": self._handle_hw_door_bell,
            "access.data.setting.update": self._handle_settings_update,
            "access.data.device.remote_unlock": self._handle_remote_unlock,
        }
        self.client.start_websocket(
            handlers,
            on_connect=on_connect,
            on_disconnect=on_disconnect,
        )

    async def async_close(self) -> None:
        """Close the API client (stops websocket)."""
        await self.client.close()

    # ------------------------------------------------------------------
    # WebSocket helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_lock_dps(
        state: DoorState, *, dps: DoorPositionStatus, lock: str
    ) -> None:
        """Apply lock relay and door position updates to a door state."""
        updates: dict[str, DoorPositionStatus | DoorLockRelayStatus] = {
            "door_position_status": dps,
        }
        if lock == "locked":
            updates["door_lock_relay_status"] = DoorLockRelayStatus.LOCK
        elif lock == "unlocked":
            updates["door_lock_relay_status"] = DoorLockRelayStatus.UNLOCK
        state.door = state.door.with_updates(**updates)

    # ------------------------------------------------------------------
    # WebSocket handlers
    # ------------------------------------------------------------------

    async def _handle_location_update(self, msg: WebsocketMessage) -> None:
        """Handle location_update_v2 messages."""
        update: LocationUpdateV2 = msg  # type: ignore[assignment]
        door_id = update.data.id

        state = self.doors.get(door_id)
        if state is None:
            return

        # Update door with fields from the websocket
        ws_state = update.data.state
        if ws_state is not None:
            self._apply_lock_dps(state, dps=ws_state.dps, lock=ws_state.lock)

            state.lock_rule = ""
            state.lock_rule_ended_time = 0
            if ws_state.remain_lock is not None:
                state.lock_rule = ws_state.remain_lock.type.value
                state.lock_rule_ended_time = ws_state.remain_lock.until
            elif ws_state.remain_unlock is not None:
                state.lock_rule = ws_state.remain_unlock.type.value
                state.lock_rule_ended_time = ws_state.remain_unlock.until

        # Handle thumbnail
        if update.data.thumbnail is not None:
            await self._update_thumbnail(
                state,
                update.data.thumbnail.url,
                update.data.thumbnail.door_thumbnail_last_update,
            )

        _LOGGER.info(
            "Location update V2 door %s (%s): locked=%s dps=%s rule=%s",
            state.name,
            state.id,
            state.door_lock_relay_status,
            state.door_position_status,
            state.lock_rule,
        )
        self._notify_doors_updated()

    async def _handle_remote_view(self, msg: WebsocketMessage) -> None:
        """Handle remote_view (doorbell press start) messages."""
        update: RemoteView = msg  # type: ignore[assignment]
        door_name = update.data.door_name
        normalized = _normalize_name(door_name)

        state = next(
            (s for s in self.doors.values() if _normalize_name(s.name) == normalized),
            None,
        )
        if state is None:
            _LOGGER.warning("Could not find door with name '%s'", door_name)
            return

        state.doorbell_request_id = update.data.request_id
        event_attributes = {
            "door_name": state.name,
            "door_id": state.id,
            "type": DOORBELL_START_EVENT,
        }
        _LOGGER.info(
            "Doorbell press on %s request id %s",
            door_name,
            update.data.request_id,
        )
        self._notify_doors_updated()
        state.trigger_event("doorbell_press", event_attributes)
        # Emit a "last_access" event of kind "doorbell" for the ring.
        await self._emit_last_access(
            state,
            actor="",
            method="",
            direction="",
            result="",
            reader="",
            kind="doorbell",
        )

    async def _handle_remote_view_change(self, msg: WebsocketMessage) -> None:
        """Handle remote_view.change (doorbell press stop) messages."""
        update: RemoteViewChange = msg  # type: ignore[assignment]
        request_id = update.data.remote_call_request_id

        state = next(
            (s for s in self.doors.values() if s.doorbell_request_id == request_id),
            None,
        )
        if state is None:
            return

        state.doorbell_request_id = None
        event_attributes = {
            "door_name": state.name,
            "door_id": state.id,
            "type": DOORBELL_STOP_EVENT,
        }
        _LOGGER.info("Doorbell press stopped on %s", state.name)
        self._notify_doors_updated()
        state.trigger_event("doorbell_press", event_attributes)

    async def _handle_device_update(self, msg: WebsocketMessage) -> None:
        """Handle device update messages."""
        update: DeviceUpdate = msg  # type: ignore[assignment]
        device_id = update.data.unique_id
        device_type = update.data.device_type
        door_id = update.data.door.unique_id if update.data.door else None

        if door_id and door_id in self.doors:
            state = self.doors[door_id]
            if state.hub_id is None:
                state.hub_type = device_type
                state.hub_id = device_id
                _LOGGER.debug(
                    "Door %s (%s) associated with hub %s (%s)",
                    state.name,
                    state.id,
                    device_type,
                    device_id,
                )
                self._notify_doors_updated()

        # If this is a known reader, refresh its access-method settings so
        # external UniFi UI changes are picked up.
        if device_id in self.readers and self.create_task:
            self.create_task(self.async_refresh_reader_settings(device_id))

    def _resolve_door_state(
        self, reported_id: str, msg: WebsocketMessage | None = None
    ) -> DoorState | None:
        """Resolve a :class:`DoorState` from any WS-reported door identifier.

        UniFi reports one of several legitimate identifier classes in the same
        field, depending on the door's hardware pairing and the API version:

        - **Door UUID** — standalone UA-G2-* doors hit ``self.doors`` directly.
        - **Server-resolved ``msg.door_id``** — newer API versions carry the
          canonical door UUID on the WebSocket message itself.
        - **Bound UAH hub id** — hub-attached doors; each ``DoorState`` records
          this in ``hub_id`` (populated at setup by ``_map_hub_types`` and by
          ``_handle_device_update`` / ``_handle_v2_device_update``).
        - **Reader device id** — UA-Intercom doors, where the reader *is* the
          access device. The reader→door mapping is populated from the
          ``/devices`` discovery (``self.readers[device_id].door_id``).
        - **Any device MAC on a known door** — ``_device_door_map`` (built from
          the raw ``/devices`` list) catches remaining device/hub MACs.

        Resolutions are cached in ``self._door_id_index`` so subsequent lookups
        for the same identifier are O(1). A cached entry pointing to a
        since-removed door is re-resolved on the next lookup.
        """
        canonical = self._door_id_index.get(reported_id)
        if canonical is not None:
            state = self.doors.get(canonical)
            if state is not None:
                return state
            # Cached door has been removed — drop the stale entry and re-resolve.
            del self._door_id_index[reported_id]

        state, via = self._resolve_door_state_uncached(reported_id, msg)
        if state is not None:
            self._door_id_index[reported_id] = state.id
            _LOGGER.debug(
                "Resolved door %s (%s) from WS-reported id %s via %s",
                state.name,
                state.id,
                reported_id,
                via,
            )
        return state

    def _resolve_door_state_uncached(
        self, reported_id: str, msg: WebsocketMessage | None = None
    ) -> tuple[DoorState | None, str]:
        """Try each identifier class once. Returns ``(state, via)`` or ``(None, "")``."""
        state = self.doors.get(reported_id)
        if state is not None:
            return state, "door-id"
        # Server-resolved door id carried on the message (newer API).
        msg_door_id = getattr(msg, "door_id", "") if msg is not None else ""
        if isinstance(msg_door_id, str) and msg_door_id:
            state = self.doors.get(msg_door_id)
            if state is not None:
                return state, "msg-door-id"
        state = next(
            (
                door
                for door in self.doors.values()
                if getattr(door, "hub_id", None) == reported_id
            ),
            None,
        )
        if state is not None:
            return state, "hub-id"
        reader = self.readers.get(reported_id)
        if reader is not None:
            state = self.doors.get(reader.door_id)
            if state is not None:
                return state, "reader-device-id"
        mapped_door_id = self._device_door_map.get(reported_id)
        if mapped_door_id:
            state = self.doors.get(mapped_door_id)
            if state is not None:
                return state, "device-door-map"
        return None, ""

    def _resolve_reader_name(self, reader_id: str | None, fallback: str | None) -> str:
        """Return a friendly reader name.

        Prefers the discovered :class:`ReaderState` (so the name matches the
        reader device shown in HA), falling back to the name reported in the
        WebSocket payload.
        """
        if reader_id and reader_id in self.readers:
            return self.readers[reader_id].name
        return fallback or ""

    def _is_duplicate_access(
        self,
        dedup: dict[str, tuple[float, str]],
        door_id: str,
        signature_values: tuple,
    ) -> bool:
        """Return whether this access duplicates a recent one for the door.

        The same physical access can arrive via both ``insights.add`` and
        ``logs.add``. A non-duplicate records its signature; a matching
        signature within ``_ACCESS_DEDUP_WINDOW`` is a duplicate.

        The signature omits the access method / authentication field, which the
        two sources report differently for the same access (insights: the
        opened-method display name; logs: the credential provider).
        """
        signature = "|".join(str(value) for value in signature_values)
        now = time.monotonic()
        previous = dedup.get(door_id)
        if (
            previous is not None
            and previous[1] == signature
            and now - previous[0] < _ACCESS_DEDUP_WINDOW
        ):
            return True
        dedup[door_id] = (now, signature)
        return False

    async def _emit_last_access(
        self,
        state: DoorState,
        *,
        actor: str,
        method: str,
        direction: str,
        result: str,
        reader: str,
        kind: str = "",
    ) -> None:
        """Fire the additive "last_access" event for a door, deduplicated.

        ``kind`` is an optional discriminator (empty for a normal access,
        ``"doorbell"`` for a doorbell ring). It is part of the dedup signature
        so a doorbell at a given door doesn't collide with an unknown-actor
        access at the same door within the dedup window.
        """
        if self._is_duplicate_access(
            self._last_access_dedup, state.id, (actor, direction, result, kind)
        ):
            return
        state.trigger_event(
            "last_access",
            {
                "door_name": state.name,
                "door_id": state.id,
                "actor": actor,
                "method": method,
                "direction": direction,
                "result": result,
                "reader": reader,
                "kind": kind,
                "capture_id": await self._capture_for_event(state.id),
            },
        )

    async def _capture_for_event(self, door_id: str) -> str:
        """Return the capture id identifying an event's snapshot image.

        The controller publishes the snapshot and the access record on
        independent paths, so either may arrive first. A snapshot that landed
        moments ago is stored right away; otherwise the id is held open for the
        snapshot still to come. Returns an empty string when no capture store
        is configured, in which case no image is recorded.
        """
        if self.captures is None:
            return ""

        capture_id = self.captures.new_id(door_id)
        recent = self._recent_thumbnail.pop(door_id, None)
        if recent is not None and time.monotonic() - recent[1] <= (
            _CAPTURE_BACKFILL_WINDOW
        ):
            _LOGGER.debug("Claiming preceding snapshot for door %s", door_id)
            await self.captures.async_save(capture_id, recent[0])
        else:
            self._pending_capture[door_id] = (capture_id, time.monotonic())
        return capture_id

    async def _update_thumbnail(
        self, state: DoorState, url: str, last_update: int | None
    ) -> bool:
        """Fetch a door thumbnail and keep it as an event's capture image.

        A thumbnail claimed by a preceding event is stored under that event's
        id; an unclaimed one is held briefly so an event arriving right after
        it can still claim it. Returns whether the thumbnail was fetched.
        """
        try:
            image = await self.client.get_thumbnail(url)
        except (ApiError, TimeoutError, ValueError):
            _LOGGER.debug("Failed to fetch thumbnail for door %s", state.id)
            return False

        state.thumbnail = image
        if last_update is not None:
            try:
                state.thumbnail_last_updated = datetime.fromtimestamp(
                    last_update, tz=UTC
                )
            except (OSError, OverflowError, ValueError):
                _LOGGER.debug(
                    "Unusable thumbnail timestamp %s for door %s",
                    last_update,
                    state.id,
                )

        if self.captures is None:
            return True

        pending = self._pending_capture.pop(state.id, None)
        if pending is not None and time.monotonic() - pending[1] <= _CAPTURE_WINDOW:
            await self.captures.async_save(pending[0], image)
        else:
            self._recent_thumbnail[state.id] = (image, time.monotonic())
        return True

    async def _handle_logs_add(self, msg: WebsocketMessage) -> None:
        """Handle access log messages.

        Fires access events as a fallback for hubs that send ``logs.add``
        but not ``insights.add``.
        """
        update: LogAdd = msg  # type: ignore[assignment]
        source = update.data.source

        door_target = next((t for t in source.target if t.type == "door"), None)
        if door_target is None:
            return

        _LOGGER.debug(
            "Log add for door %s: %s by %s (%s)",
            door_target.id,
            source.event.result,
            source.actor.display_name,
            source.authentication.credential_provider,
        )

        # Resolve to the canonical door id so the insights/logs dedup keys on
        # the same id; the reported id may be a hub/reader/device MAC.
        state = self._resolve_door_state(door_target.id, msg)
        if state is None:
            _LOGGER.warning(
                "Could not find door for log event with reported id %s "
                "(tried door UUID, msg door id, hub id, reader device id, "
                "device map)",
                door_target.id,
            )
            return

        # Fire access events from logs.add as fallback — but skip if
        # insights.add already fired for this door recently.
        last_insight = self._last_insight_time.get(state.id, 0.0)
        if time.monotonic() - last_insight < 5.0:
            return

        device_config = source.device_config
        if device_config is None:
            return

        access_type = device_config.display_name.lower()
        if access_type == "entry":
            event_type = ACCESS_ENTRY_EVENT
        elif access_type == "exit":
            event_type = ACCESS_EXIT_EVENT
        else:
            event_type = ACCESS_GENERIC_EVENT

        event_attributes = {
            "door_name": state.name,
            "door_id": state.id,
            "actor": source.actor.display_name,
            "authentication": source.authentication.credential_provider,
            "type": event_type,
            "result": source.event.result,
        }
        if not self._is_duplicate_access(
            self._access_event_dedup,
            state.id,
            (source.actor.display_name, event_type, source.event.result),
        ):
            state.trigger_event("access", event_attributes)

        # Fire a separate "last_access" event carrying the reader.
        reader_target = next(
            (
                t
                for t in source.target
                if str(getattr(t, "type", "")).startswith("UA-")
                and not str(getattr(t, "type", "")).startswith("UA-Hub")
            ),
            None,
        )
        reader_name = ""
        if reader_target is not None:
            reader_name = self._resolve_reader_name(
                getattr(reader_target, "id", None),
                getattr(reader_target, "name", None)
                or getattr(reader_target, "display_name", None)
                or getattr(reader_target, "type", None),
            )
        await self._emit_last_access(
            state,
            actor=source.actor.display_name,
            method=source.authentication.credential_provider,
            direction=access_type if access_type in ("entry", "exit") else "",
            result=source.event.result,
            reader=reader_name,
        )

    async def _handle_hw_door_bell(self, msg: WebsocketMessage) -> None:
        """Handle hardware doorbell press messages."""
        update: HwDoorbell = msg  # type: ignore[assignment]
        door_id = update.data.door_id
        door_name = update.data.door_name

        state = self.doors.get(door_id)
        if state is None:
            return

        state.doorbell_request_id = update.data.request_id
        event_attributes = {
            "door_name": state.name,
            "door_id": state.id,
            "type": DOORBELL_START_EVENT,
        }
        _LOGGER.info("Hardware doorbell press on %s (%s)", door_name, door_id)
        self._notify_doors_updated()
        state.trigger_event("doorbell_press", event_attributes)
        # Emit a "last_access" event of kind "doorbell" for the ring.
        await self._emit_last_access(
            state,
            actor="",
            method="",
            direction="",
            result="",
            reader="",
            kind="doorbell",
        )

        # Schedule automatic stop after 2 seconds
        captured_request_id = update.data.request_id

        async def _auto_stop() -> None:
            await asyncio.sleep(2)
            if state.doorbell_request_id != captured_request_id:
                return
            state.doorbell_request_id = None
            stop_attrs = {
                "door_name": state.name,
                "door_id": state.id,
                "type": DOORBELL_STOP_EVENT,
            }
            self._notify_doors_updated()
            state.trigger_event("doorbell_press", stop_attrs)

        if self.create_task:
            self.create_task(_auto_stop())
        else:
            _LOGGER.warning("Cannot schedule doorbell auto-stop: create_task not set")

    async def _handle_insights_add(self, msg: WebsocketMessage) -> None:
        """Handle insights add (access entry/exit) events."""
        update: InsightsAdd = msg  # type: ignore[assignment]
        door_entries = update.data.metadata.door
        if not door_entries:
            _LOGGER.debug("Ignoring insights event without door metadata: %s", update)
            return
        reported_door_id = door_entries[0].id
        state = self._resolve_door_state(reported_door_id, msg)
        if state is None:
            _LOGGER.warning(
                "Could not find door for insights event with reported id %s "
                "(tried door UUID, msg door id, hub id, reader device id, "
                "device map)",
                reported_door_id,
            )
            return

        canonical_door_id = state.id

        direction_entries = update.data.metadata.opened_direction
        direction = (
            direction_entries[0].display_name.lower() if direction_entries else ""
        )
        if direction == "entry":
            event_type = ACCESS_ENTRY_EVENT
        elif direction == "exit":
            event_type = ACCESS_EXIT_EVENT
        else:
            event_type = ACCESS_GENERIC_EVENT

        method_entries = update.data.metadata.opened_method
        method = method_entries[0].display_name if method_entries else ""

        event_attributes = {
            "door_name": state.name,
            "door_id": state.id,
            "actor": update.data.metadata.actor.display_name,
            "authentication": update.data.metadata.authentication.display_name,
            "type": event_type,
            "method": method,
            "result": update.data.result,
        }
        _LOGGER.info(
            "Insight: %s on %s (%s) by %s via %s: %s",
            update.data.event_type,
            state.name,
            state.id,
            update.data.metadata.actor.display_name,
            update.data.metadata.authentication.display_name,
            update.data.result,
        )
        self._last_insight_time[canonical_door_id] = time.monotonic()
        if not self._is_duplicate_access(
            self._access_event_dedup,
            state.id,
            (update.data.metadata.actor.display_name, event_type, update.data.result),
        ):
            state.trigger_event("access", event_attributes)

        # Fire a separate "last_access" event carrying the reader. The reader
        # identity is in the ``device_ua_reader`` metadata key
        # (``{id, type, display_name}``).
        reader = getattr(update.data.metadata, "device_ua_reader", None)
        reader_name = ""
        if reader is not None:
            if isinstance(reader, dict):
                reader_id = reader.get("id")
                reader_fallback = reader.get("display_name") or reader.get("type")
            else:
                reader_id = getattr(reader, "id", None)
                reader_fallback = getattr(reader, "display_name", None) or getattr(
                    reader, "type", None
                )
            reader_name = self._resolve_reader_name(reader_id, reader_fallback)
        await self._emit_last_access(
            state,
            actor=update.data.metadata.actor.display_name,
            method=method,
            direction=direction if direction in ("entry", "exit") else "",
            result=update.data.result,
            reader=reader_name,
        )

    async def _handle_v2_location_update(self, msg: WebsocketMessage) -> None:
        """Handle V2 location update messages."""
        update: V2LocationUpdate = msg  # type: ignore[assignment]
        door_id = update.data.id

        state = self.doors.get(door_id)
        if state is None:
            return

        ws_state = update.data.state
        if ws_state is not None:
            self._apply_lock_dps(state, dps=ws_state.dps, lock=ws_state.lock)

            # Lock rules
            state.lock_rule = ""
            state.lock_rule_ended_time = 0
            if ws_state.remain_lock is not None:
                state.lock_rule = ws_state.remain_lock.type.value
                state.lock_rule_ended_time = ws_state.remain_lock.until
            elif ws_state.remain_unlock is not None:
                state.lock_rule = ws_state.remain_unlock.type.value
                state.lock_rule_ended_time = ws_state.remain_unlock.until

        # Handle thumbnail
        if update.data.thumbnail is not None:
            await self._update_thumbnail(
                state,
                update.data.thumbnail.url,
                update.data.thumbnail.door_thumbnail_last_update,
            )

        _LOGGER.info(
            "V2 location update door %s (%s): locked=%s dps=%s rule=%s",
            state.name,
            state.id,
            state.door_lock_relay_status,
            state.door_position_status,
            state.lock_rule,
        )
        self._notify_doors_updated()

    async def _handle_v2_device_update(self, msg: WebsocketMessage) -> None:
        """Handle V2 device update messages."""
        update: V2DeviceUpdate = msg  # type: ignore[assignment]
        device_id = update.data.id
        device_type = update.data.device_type

        updated = False
        for loc_state in update.data.location_states:
            door_id = loc_state.location_id
            state = self.doors.get(door_id)
            if state is None:
                continue

            if state.hub_id is None:
                state.hub_type = device_type
                state.hub_id = device_id

            self._apply_lock_dps(state, dps=loc_state.dps, lock=loc_state.lock)

            # Lock rules
            state.lock_rule = ""
            state.lock_rule_ended_time = 0
            if loc_state.remain_lock is not None:
                state.lock_rule = loc_state.remain_lock.type.value
                state.lock_rule_ended_time = loc_state.remain_lock.until
            elif loc_state.remain_unlock is not None:
                state.lock_rule = loc_state.remain_unlock.type.value
                state.lock_rule_ended_time = loc_state.remain_unlock.until

            updated = True

        _LOGGER.debug(
            "V2 device update %s (%s): online=%s firmware=%s",
            update.data.alias or update.data.name,
            device_id,
            update.data.online,
            update.data.firmware,
        )

        # If this is a known reader, refresh its access-method settings.
        if device_id in self.readers and self.create_task:
            self.create_task(self.async_refresh_reader_settings(device_id))

        if updated:
            self._notify_doors_updated()

    async def _handle_location_update_legacy(self, msg: WebsocketMessage) -> None:
        """Handle legacy (V1) location update messages."""
        update: LocationUpdateLegacy = msg  # type: ignore[assignment]
        door_id = update.data.unique_id

        state = self.doors.get(door_id)
        if state is None:
            return

        updated = False
        extras = update.data.extras
        if extras is not None:
            thumb_url = extras.get("door_thumbnail")
            thumb_ts = extras.get("door_thumbnail_last_update")
            if thumb_url and isinstance(thumb_url, str):
                try:
                    stamp = None if thumb_ts is None else int(thumb_ts)
                except (TypeError, ValueError):
                    stamp = None
                updated = await self._update_thumbnail(state, thumb_url, stamp)

        _LOGGER.debug(
            "Legacy location update door %s (%s)",
            state.name,
            state.id,
        )
        if updated:
            self._notify_doors_updated()

    async def _handle_base_info(self, msg: WebsocketMessage) -> None:
        """Handle base info (log counter) messages."""
        update: BaseInfo = msg  # type: ignore[assignment]
        _LOGGER.debug("Base info: top_log_count=%s", update.data.top_log_count)

    async def _handle_settings_update(self, msg: WebsocketMessage) -> None:
        """Handle settings update (evacuation/lockdown + device access-methods) messages."""
        update: SettingUpdate = msg  # type: ignore[assignment]
        self.evacuation = update.data.evacuation
        self.lockdown = update.data.lockdown
        _LOGGER.info(
            "Settings updated: evacuation=%s lockdown=%s",
            self.evacuation,
            self.lockdown,
        )
        self._notify_emergency_updated()

        # Also refresh every reader's access-method settings — this event may
        # be fired when access methods are changed in the UniFi UI.
        if self.create_task:
            for device_id in self.readers:
                self.create_task(self.async_refresh_reader_settings(device_id))

    async def _handle_remote_unlock(self, msg: WebsocketMessage) -> None:
        """Handle remote door unlock messages."""
        update: RemoteUnlock = msg  # type: ignore[assignment]
        door_id = update.data.unique_id

        state = self.doors.get(door_id)
        if state is None:
            return

        state.door = state.door.with_updates(
            door_lock_relay_status=DoorLockRelayStatus.UNLOCK
        )
        _LOGGER.info("Remote unlock on %s (%s)", state.name, state.id)
        self._notify_doors_updated()
