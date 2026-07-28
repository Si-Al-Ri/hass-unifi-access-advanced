"""Guest-pass actions for the Unifi Access integration."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime

from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util
import voluptuous as vol

from .const import DOMAIN
from .guest_pass import CREDENTIAL_TYPES, GuestPassManager

SERVICE_CREATE = "create_guest_pass"
SERVICE_REVOKE = "revoke_guest_pass"
SERVICE_EXTEND = "extend_guest_pass"
SERVICE_LIST = "list_guest_passes"

_SERVICES = (
    SERVICE_CREATE,
    SERVICE_REVOKE,
    SERVICE_EXTEND,
    SERVICE_LIST,
)

_CREATE_SCHEMA = vol.Schema(
    {
        vol.Required("name"): cv.string,
        # Accepts a single door id or a list — always normalized to a list.
        vol.Required("door_id"): vol.All(
            cv.ensure_list, [cv.string], vol.Length(min=1)
        ),
        vol.Required("valid_from"): cv.datetime,
        vol.Required("valid_until"): cv.datetime,
        vol.Optional("credentials", default=["pin"]): vol.All(
            cv.ensure_list, [vol.In(CREDENTIAL_TYPES)]
        ),
    }
)
_REVOKE_SCHEMA = vol.Schema({vol.Required("visitor_id"): cv.string})
_EXTEND_SCHEMA = vol.Schema(
    {
        vol.Required("visitor_id"): cv.string,
        vol.Required("valid_from"): cv.datetime,
        vol.Required("valid_until"): cv.datetime,
    }
)


def _to_epoch(value: datetime) -> int:
    """Convert a (possibly naive) datetime to a Unix timestamp.

    A naive datetime is interpreted in Home Assistant's local time zone.
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
    return int(value.timestamp())


def _managers(hass: HomeAssistant) -> Iterator[GuestPassManager]:
    """Yield the GuestPassManager of every loaded config entry."""
    for entry in hass.config_entries.async_entries(DOMAIN):
        data = getattr(entry, "runtime_data", None)
        if data is not None:
            yield data.guest_passes


def _manager_for_doors(hass: HomeAssistant, door_ids: list[str]) -> GuestPassManager:
    """Return the manager of the controller that owns ``door_ids``.

    All doors must belong to the same controller (a visitor pass cannot span
    controllers).
    """
    for entry in hass.config_entries.async_entries(DOMAIN):
        data = getattr(entry, "runtime_data", None)
        if data is None or not any(d in data.hub.doors for d in door_ids):
            continue
        missing = [d for d in door_ids if d not in data.hub.doors]
        if missing:
            raise ServiceValidationError(
                "All doors must belong to the same UniFi Access controller; "
                f"unknown on this controller: {', '.join(missing)}"
            )
        return data.guest_passes
    raise ServiceValidationError(
        f"No UniFi Access door found for: {', '.join(door_ids)}"
    )


def _manager_for_visitor(hass: HomeAssistant, visitor_id: str) -> GuestPassManager:
    """Return the manager that knows ``visitor_id`` (or the sole controller)."""
    managers = list(_managers(hass))
    for manager in managers:
        if manager.has_pass(visitor_id):
            return manager
    if len(managers) == 1:
        return managers[0]
    raise ServiceValidationError(
        f"Guest pass '{visitor_id}' is not known to any UniFi Access controller"
    )


async def _handle_create(call: ServiceCall) -> ServiceResponse:
    """Handle the create_guest_pass service."""
    door_ids = call.data["door_id"]
    manager = _manager_for_doors(call.hass, door_ids)
    try:
        return await manager.async_create(
            name=call.data["name"],
            door_ids=door_ids,
            valid_from=_to_epoch(call.data["valid_from"]),
            valid_until=_to_epoch(call.data["valid_until"]),
            credentials=call.data["credentials"],
        )
    except (RuntimeError, ValueError) as err:
        raise HomeAssistantError(str(err)) from err


async def _handle_revoke(call: ServiceCall) -> None:
    """Handle the revoke_guest_pass service."""
    manager = _manager_for_visitor(call.hass, call.data["visitor_id"])
    try:
        await manager.async_revoke(call.data["visitor_id"])
    except RuntimeError as err:
        raise HomeAssistantError(str(err)) from err


async def _handle_extend(call: ServiceCall) -> ServiceResponse:
    """Handle the extend_guest_pass service."""
    manager = _manager_for_visitor(call.hass, call.data["visitor_id"])
    try:
        return await manager.async_extend(
            call.data["visitor_id"],
            _to_epoch(call.data["valid_from"]),
            _to_epoch(call.data["valid_until"]),
        )
    except RuntimeError as err:
        raise HomeAssistantError(str(err)) from err


async def _handle_list(call: ServiceCall) -> ServiceResponse:
    """Return the available doors and all registered guest passes."""
    doors: list[dict[str, str]] = []
    passes: list[dict] = []
    seen: set[str] = set()
    for entry in call.hass.config_entries.async_entries(DOMAIN):
        data = getattr(entry, "runtime_data", None)
        if data is None:
            continue
        for door_id, door in data.hub.doors.items():
            if door_id not in seen:
                seen.add(door_id)
                doors.append({"id": door_id, "name": door.name})
        passes.extend(await data.guest_passes.async_list())
    return {"doors": doors, "passes": passes}


def async_setup_services(hass: HomeAssistant) -> None:
    """Register the guest-pass services (once for the whole integration)."""
    if hass.services.has_service(DOMAIN, SERVICE_CREATE):
        return
    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE,
        _handle_create,
        schema=_CREATE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REVOKE,
        _handle_revoke,
        schema=_REVOKE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_EXTEND,
        _handle_extend,
        schema=_EXTEND_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_LIST,
        _handle_list,
        supports_response=SupportsResponse.ONLY,
    )


def async_unload_services(hass: HomeAssistant) -> None:
    """Remove the guest-pass services."""
    for service in _SERVICES:
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)
