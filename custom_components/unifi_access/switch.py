"""Platform for switch integration."""

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from unifi_access_api import EmergencyStatus

from . import UnifiAccessConfigEntry
from .const import ANTI_SPOOFING_COMBOS, DOMAIN
from .coordinator import UnifiAccessCoordinator
from .entity import UnifiAccessReaderEntity
from .hub import DoorState, ReaderState, UnifiAccessHub

PARALLEL_UPDATES = 1

# Access methods exposed as simple on/off switches. Face unlock has its own
# switch and anti-spoofing select, and is not included here. bt_shake and
# mobile_wave are reported by the settings endpoint but not exposed.
_ACCESS_METHOD_KEYS = (
    "nfc",
    "bt_button",
    "bt_tap",
    "pin_code",
    "wave",
    "qr_code",
    "touch_pass",
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: UnifiAccessConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add switch entities for passed config entry."""
    data = config_entry.runtime_data

    # Emergency switches are always present.
    async_add_entities(
        [
            EmergencySwitch(
                data.hub,
                data.emergency_coordinator,
                field="evacuation",
                unique_id="unifi_access_all_doors_evacuation",
                translation_key="evacuation",
            ),
            EmergencySwitch(
                data.hub,
                data.emergency_coordinator,
                field="lockdown",
                unique_id="unifi_access_all_doors_lockdown",
                translation_key="lockdown",
            ),
        ]
    )

    # Reader switches are created once a reader's access-method settings are
    # known: a face-unlock switch (if the hardware supports it) plus one switch
    # per access method the reader actually reports and supports.
    added_readers: set[str] = set()

    def on_reader_ready(device_id: str) -> None:
        if device_id in added_readers:
            return
        reader = data.hub.readers.get(device_id)
        if reader is None or reader.access_methods is None:
            return
        added_readers.add(device_id)
        entities: list[SwitchEntity] = []
        if reader.supports_face:
            entities.append(UnifiFaceUnlockSwitch(data.hub, reader, data.coordinator))
        entities.extend(
            UnifiAccessMethodSwitch(data.hub, reader, data.coordinator, method)
            for method in _ACCESS_METHOD_KEYS
            # Method must be reported by the reader AND supported by the
            # hardware — the settings endpoint lists some (e.g. touch_pass)
            # the device cannot actually use.
            if method in reader.access_methods and reader.supports_method(method)
        )
        if entities:
            async_add_entities(entities)

    data.hub.register_reader_callback(on_reader_ready)


class EmergencySwitch(CoordinatorEntity, SwitchEntity):
    """Unifi Access Emergency Switch (Evacuation / Lockdown)."""

    _attr_has_entity_name = True

    def __init__(
        self,
        hub: UnifiAccessHub,
        coordinator: UnifiAccessCoordinator[EmergencyStatus],
        *,
        field: str,
        unique_id: str,
        translation_key: str,
    ) -> None:
        """Initialize Unifi Access Emergency Switch."""
        super().__init__(coordinator, context=field)
        self.hub = hub
        self._field = field
        self._attr_unique_id = unique_id
        self._attr_translation_key = translation_key

    @property
    def device_info(self) -> DeviceInfo:
        """Get device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, "unifi_access_all_doors")},
            name="All Doors",
            model="UAH",
            manufacturer="Unifi",
        )

    @property
    def is_on(self) -> bool:
        """Get switch status."""
        return bool(getattr(self.hub, self._field))

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off emergency mode."""
        await self.hub.async_set_emergency_status(**{self._field: False})

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on emergency mode."""
        await self.hub.async_set_emergency_status(**{self._field: True})


class UnifiFaceUnlockSwitch(UnifiAccessReaderEntity, SwitchEntity):
    """Switch to enable / disable face unlock on a UniFi Access reader."""

    _attr_translation_key = "face_unlock"

    def __init__(
        self,
        hub: UnifiAccessHub,
        reader: ReaderState,
        coordinator: UnifiAccessCoordinator[dict[str, DoorState]],
    ) -> None:
        """Initialize the face unlock switch."""
        super().__init__(hub, reader, coordinator)
        self._attr_unique_id = f"{reader.device_id}_face_unlock"

    async def async_added_to_hass(self) -> None:
        """Trigger an initial settings fetch when HA adds this entity."""
        await super().async_added_to_hass()
        if self.reader.access_methods is None:
            await self._hub.async_refresh_reader_settings(self.reader.device_id)

    @property
    def is_on(self) -> bool | None:
        """Return True when face unlock is enabled."""
        if self.reader.access_methods is None:
            return None
        return self.reader.access_methods.get("face", {}).get("enabled") == "yes"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable face unlock, preserving the configured anti-spoofing combo."""
        face_payload: dict[str, str] = {"enabled": "yes"}
        # Send the last-known valid (anti_spoofing_level, detect_distance) pair
        # so enabling face unlock keeps the configured security level.
        combo = self.reader.last_anti_spoofing_combo
        if combo in ANTI_SPOOFING_COMBOS:
            level, distance = ANTI_SPOOFING_COMBOS[combo]
            face_payload["anti_spoofing_level"] = level
            face_payload["detect_distance"] = distance
        await self._write({"face": face_payload})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable face unlock."""
        await self._write({"face": {"enabled": "no"}})

    async def _write(self, access_methods: dict) -> None:
        try:
            await self._hub.async_update_reader_settings(
                self.reader.device_id, {"access_methods": access_methods}
            )
        except RuntimeError as err:
            raise HomeAssistantError(str(err)) from err
        await self._hub.async_refresh_reader_settings(self.reader.device_id)


class UnifiAccessMethodSwitch(UnifiAccessReaderEntity, SwitchEntity):
    """Switch to enable / disable a single UniFi Access access method."""

    def __init__(
        self,
        hub: UnifiAccessHub,
        reader: ReaderState,
        coordinator: UnifiAccessCoordinator[dict[str, DoorState]],
        method: str,
    ) -> None:
        """Initialize the access-method switch."""
        super().__init__(hub, reader, coordinator)
        self.method = method
        self._attr_translation_key = method
        self._attr_unique_id = f"{reader.device_id}_{method}"

    @property
    def is_on(self) -> bool | None:
        """Return True when this access method is enabled."""
        if self.reader.access_methods is None:
            return None
        return self.reader.access_methods.get(self.method, {}).get("enabled") == "yes"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable this access method."""
        await self._async_set_enabled(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable this access method."""
        await self._async_set_enabled(False)

    async def _async_set_enabled(self, enabled: bool) -> None:
        payload = {
            "access_methods": {self.method: {"enabled": "yes" if enabled else "no"}}
        }
        try:
            await self._hub.async_update_reader_settings(self.reader.device_id, payload)
        except RuntimeError as err:
            raise HomeAssistantError(str(err)) from err
        await self._hub.async_refresh_reader_settings(self.reader.device_id)
