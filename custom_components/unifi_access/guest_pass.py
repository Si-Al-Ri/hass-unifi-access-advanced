"""Guest pass management for the Unifi Access integration.

Creates, revokes and reactivates time-limited UniFi Access visitor passes
(PIN and/or QR) and keeps a persistent registry of the passes created via HA.
The registry stores the PIN/QR so they can be shown again while the pass is
active; the list is reconciled against UniFi on every read so it mirrors the
UniFi visitor list (a pass deleted in the UniFi web UI drops out of HA too).
"""

from __future__ import annotations

import base64
from collections.abc import Callable, Iterable
import contextlib
import time
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN, EVENT_GUEST_ARRIVED
from .hub import DoorState, UnifiAccessHub

_STORE_VERSION = 1
CREDENTIAL_TYPES = ("pin", "qr")

# UniFi visitor status enum → card status key.
_STATUS_MAP = {
    "UPCOMING": "upcoming",
    "ACTIVE": "upcoming",
    "VISITING": "arrived",
    "VISITED": "expired",
    "NO_VISIT": "expired",
    "CANCELLED": "revoked",
}
_ACTIVE_KEYS = ("upcoming", "arrived")


def split_name(name: str) -> tuple[str, str]:
    """Split a single name field into (first_name, last_name).

    UniFi Access requires both to be non-empty; a single-word name gets the
    last name "Gast".
    """
    parts = name.strip().split(" ", 1)
    first = parts[0].strip() or "Gast"
    last = parts[1].strip() if len(parts) > 1 and parts[1].strip() else "Gast"
    return first, last


def _matches_pass(actor: str, pass_name: str) -> bool:
    """Return whether an access actor name matches a guest pass name.

    UniFi formats the actor as the visitor's full name ("First Last").
    ``split_name`` normalises the pass name into the same first/last shape.
    The match is exact on the lowercased, trimmed strings (no fuzzy matching).
    """
    actor_l = actor.strip().lower()
    if not actor_l or not pass_name:
        return False
    first, last = split_name(pass_name)
    full = f"{first} {last}".strip().lower()
    return actor_l == full or actor_l == pass_name.strip().lower()


def status_key(unifi_status: Any, valid_until: int, now: int) -> str:
    """Map a UniFi visitor status to a card status key.

    Falls back to "expired" once the validity window is over, since UniFi does
    not always flip the status promptly.
    """
    key = _STATUS_MAP.get(str(unifi_status).upper(), "expired")
    if key in _ACTIVE_KEYS and now > valid_until:
        return "expired"
    return key


class GuestPassManager:
    """Manages UniFi Access guest passes and a persistent pass registry."""

    def __init__(self, hass: HomeAssistant, hub: UnifiAccessHub, entry_id: str) -> None:
        """Initialize the manager."""
        self._hass = hass
        self._hub = hub
        self._store: Store[dict[str, Any]] = Store(
            hass, _STORE_VERSION, f"{DOMAIN}_guest_passes_{entry_id}"
        )
        self._passes: dict[str, dict[str, Any]] = {}
        # Listener-unsubscribe handles for the per-door last_access hooks.
        self._unsubs: list[Callable[[], None]] = []

    async def async_load(self) -> None:
        """Load the persisted pass registry."""
        data = await self._store.async_load()
        if data and isinstance(data.get("passes"), dict):
            self._passes = data["passes"]

    async def _async_save(self) -> None:
        await self._store.async_save({"passes": self._passes})

    def has_pass(self, visitor_id: str) -> bool:
        """Return whether a visitor id is in this manager's registry."""
        return visitor_id in self._passes

    # ------------------------------------------------------------------
    # Arrival capture via WebSocket access events
    # ------------------------------------------------------------------

    def async_start(self, doors: Iterable[DoorState]) -> None:
        """Listen to every door's last_access events to stamp arrivals.

        UniFi exposes no explicit "first arrival" field. Listening to the
        WS-fed last_access events stamps ``arrived_at`` on credential use;
        the ``async_list`` polling path stamps it as a fallback.
        """
        for door in doors:
            door.add_event_listener("last_access", self._on_access)

            def _unsub(d: DoorState = door) -> None:
                d.remove_event_listener("last_access", self._on_access)

            self._unsubs.append(_unsub)

    def async_stop(self) -> None:
        """Remove all last_access event listeners (entry unload)."""
        for unsub in self._unsubs:
            with contextlib.suppress(Exception):
                unsub()
        self._unsubs.clear()

    def _on_access(self, event: str, attributes: dict[str, str]) -> None:
        """Stamp ``arrived_at`` on the matching pending pass for an access."""
        if attributes.get("kind") == "doorbell":
            return
        actor = (attributes.get("actor") or "").strip()
        if not actor:
            return
        matches = [
            visitor_id
            for visitor_id, record in self._passes.items()
            if not record.get("arrived_at")
            and _matches_pass(actor, record.get("name", ""))
        ]
        # Only stamp on an unambiguous single match.
        if len(matches) != 1:
            return
        visitor_id = matches[0]
        self._passes[visitor_id]["arrived_at"] = int(time.time())
        self._hass.async_create_task(self._async_save())
        self._hass.bus.async_fire(EVENT_GUEST_ARRIVED, {"visitor_id": visitor_id})

    async def async_create(
        self,
        *,
        name: str,
        door_ids: list[str],
        valid_from: int,
        valid_until: int,
        credentials: list[str],
    ) -> dict[str, Any]:
        """Create a guest pass valid for one or more doors.

        Returns a result dict with the PIN (plaintext) and/or QR data URI.
        """
        creds = [c for c in credentials if c in CREDENTIAL_TYPES]
        if not creds:
            raise ValueError("At least one credential type (pin/qr) is required")
        if not door_ids:
            raise ValueError("At least one door is required")

        door_names = [
            self._hub.doors[door_id].name if door_id in self._hub.doors else door_id
            for door_id in door_ids
        ]
        door_name = ", ".join(door_names)
        first, last = split_name(name)

        pin: str | None = None
        if "pin" in creds:
            pin = await self._hub.async_generate_pin()

        visitor = await self._hub.async_create_visitor(
            first_name=first,
            last_name=last,
            start_time=valid_from,
            end_time=valid_until,
            door_ids=door_ids,
        )
        visitor_id = str(visitor["id"])

        try:
            if pin is not None:
                await self._hub.async_assign_visitor_pin(visitor_id, pin)
            if "qr" in creds:
                await self._hub.async_assign_visitor_qr(visitor_id)
        except RuntimeError:
            # Roll back the half-created visitor so no orphan is left behind.
            with contextlib.suppress(RuntimeError):
                await self._hub.async_cancel_visitor(visitor_id)
            raise

        qr_image: str | None = None
        if "qr" in creds:
            qr_image = await self._async_qr_data_uri(visitor_id)

        record: dict[str, Any] = {
            "visitor_id": visitor_id,
            "name": name,
            "door_ids": list(door_ids),
            "door_name": door_name,
            "credentials": creds,
            "valid_from": valid_from,
            "valid_until": valid_until,
            "created_at": int(time.time()),
        }
        if pin is not None:
            record["pin"] = pin
        if qr_image is not None:
            record["qr_image"] = qr_image
        self._passes[visitor_id] = record
        await self._async_save()

        result = {**record, "status": "upcoming"}
        result.pop("door_ids", None)
        result.pop("created_at", None)
        return result

    async def async_extend(
        self, visitor_id: str, valid_from: int, valid_until: int
    ) -> dict[str, Any]:
        """Reactivate / extend a pass with a new validity window.

        The controller removes a pass's credentials once it has ended (expired
        or cancelled). When such a pass is reactivated, its PIN/QR are
        re-assigned so they work again; a PIN is regenerated if the stored
        plaintext is no longer available. Credentials of a still-active pass
        are left untouched.
        """
        record = self._passes.get(visitor_id)
        creds = (record or {}).get("credentials", [])
        now = int(time.time())

        visitor = await self._hub.async_get_visitor(visitor_id)
        was_inactive = (
            visitor is None
            or status_key(visitor.get("status"), int(visitor.get("end_time") or 0), now)
            not in _ACTIVE_KEYS
        )

        await self._hub.async_update_visitor_window(visitor_id, valid_from, valid_until)

        pin = (record or {}).get("pin")
        qr_image = (record or {}).get("qr_image")
        if was_inactive:
            if "pin" in creds:
                if pin:
                    # Restore the stored PIN; a still-valid PIN raises, which
                    # is fine — it remains usable.
                    with contextlib.suppress(RuntimeError):
                        await self._hub.async_assign_visitor_pin(visitor_id, pin)
                else:
                    pin = await self._hub.async_generate_pin()
                    await self._hub.async_assign_visitor_pin(visitor_id, pin)
            if "qr" in creds:
                await self._hub.async_assign_visitor_qr(visitor_id)
                qr_image = await self._async_qr_data_uri(visitor_id)

        if record is not None:
            record["valid_from"] = valid_from
            record["valid_until"] = valid_until
            # Clear the previous arrival so the new window is shown until the
            # guest arrives again.
            record.pop("arrived_at", None)
            if pin:
                record["pin"] = pin
            if qr_image:
                record["qr_image"] = qr_image
            await self._async_save()

        result: dict[str, Any] = {
            "visitor_id": visitor_id,
            "valid_from": valid_from,
            "valid_until": valid_until,
            "status": "upcoming",
            "arrived_at": None,
            "name": (record or {}).get("name"),
            "door_name": (record or {}).get("door_name"),
            "credentials": creds,
        }
        if pin:
            result["pin"] = pin
        if qr_image:
            result["qr_image"] = qr_image
        return result

    async def async_revoke(self, visitor_id: str) -> None:
        """Revoke a guest pass.

        A soft-cancelled pass is kept in the registry (it will show as
        "revoked"); a pass already hard-deleted in UniFi is dropped.
        """
        try:
            await self._hub.async_cancel_visitor(visitor_id)
        except RuntimeError as err:
            if "not found" in str(err).lower():
                if self._passes.pop(visitor_id, None) is not None:
                    await self._async_save()
                return
            raise

    async def async_delete(self, visitor_id: str) -> None:
        """Permanently delete a guest pass and drop it from the registry.

        A pass that no longer exists in UniFi is still removed locally.
        """
        try:
            await self._hub.async_delete_visitor(visitor_id)
        except RuntimeError as err:
            if "not found" not in str(err).lower():
                raise
        if self._passes.pop(visitor_id, None) is not None:
            await self._async_save()

    async def async_list(self) -> list[dict[str, Any]]:
        """Return all passes, reconciled against UniFi.

        Passes that no longer exist in UniFi are pruned. The status and window
        are taken from UniFi; the PIN/QR are included only while the pass is
        active.
        """
        now = int(time.time())
        out: list[dict[str, Any]] = []
        changed = False
        for visitor_id in list(self._passes):
            record = self._passes[visitor_id]
            visitor = await self._hub.async_get_visitor(visitor_id)
            if visitor is None:
                del self._passes[visitor_id]
                changed = True
                continue

            vfrom = int(visitor.get("start_time") or record.get("valid_from") or 0)
            vuntil = int(visitor.get("end_time") or record.get("valid_until") or 0)
            if vfrom != record.get("valid_from") or vuntil != record.get("valid_until"):
                record["valid_from"] = vfrom
                record["valid_until"] = vuntil
                changed = True

            key = status_key(visitor.get("status"), vuntil, now)
            # Stamp the arrival the first time the status becomes "arrived"
            # and notify listeners.
            if key == "arrived" and not record.get("arrived_at"):
                record["arrived_at"] = now
                changed = True
                self._hass.bus.async_fire(
                    EVENT_GUEST_ARRIVED, {"visitor_id": visitor_id}
                )
            entry: dict[str, Any] = {
                "visitor_id": visitor_id,
                "name": record.get("name", ""),
                "door_name": record.get("door_name", ""),
                "credentials": record.get("credentials", []),
                "valid_from": vfrom,
                "valid_until": vuntil,
                "status": key,
                "arrived_at": record.get("arrived_at"),
            }
            if key in _ACTIVE_KEYS:
                if record.get("pin"):
                    entry["pin"] = record["pin"]
                if record.get("qr_image"):
                    entry["qr_image"] = record["qr_image"]
            out.append(entry)

        if changed:
            await self._async_save()
        return out

    async def _async_qr_data_uri(self, visitor_id: str) -> str:
        """Download the QR PNG and return it as a data: URI."""
        png = await self._hub.async_download_visitor_qr(visitor_id)
        encoded = base64.b64encode(png).decode("ascii")
        return f"data:image/png;base64,{encoded}"
