"""Platform for select integration."""

import logging
from typing import ClassVar

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import UnifiAccessConfigEntry, UnifiAccessData
from .const import ANTI_SPOOFING_COMBOS, DOOR_TYPES
from .coordinator import UnifiAccessCoordinator
from .entity import UnifiAccessDoorEntity, UnifiAccessReaderEntity
from .hub import DoorState, ReaderState, UnifiAccessHub

PARALLEL_UPDATES = 1

_LOGGER = logging.getLogger(__name__)

# PIN keypad layout select option ↔ pin_code.pin_code_shuffle API value.
_PIN_LAYOUT_OPTIONS = {"standard": "no", "shuffle": "yes"}
_PIN_LAYOUT_BY_SHUFFLE = {v: k for k, v in _PIN_LAYOUT_OPTIONS.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: UnifiAccessConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add select entity for passed config entry."""
    data = config_entry.runtime_data

    if data.hub.supports_door_lock_rules:
        async_add_entities(
            [
                TemporaryLockRuleSelectEntity(data, door_id)
                for door_id in data.coordinator.data
            ]
        )

    _setup_entity_type_selects(config_entry, data, async_add_entities)
    _setup_reader_selects(data, async_add_entities)


def _setup_entity_type_selects(
    config_entry: UnifiAccessConfigEntry,
    data: UnifiAccessData,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Offer an EntityTypeSelect (lock / garage / gate) for UGT gate doors.

    A door's ``hub_type`` is populated at setup (``_map_hub_types``) and may be
    updated by later WS device events, so this rescans on every coordinator
    update and adds the select once a UGT door appears.
    """
    known_ugt_doors: set[str] = set()

    def _check_for_new_ugt_doors() -> None:
        new_entities = []
        for door_id, door in data.coordinator.data.items():
            if door.hub_type == "UGT" and door_id not in known_ugt_doors:
                known_ugt_doors.add(door_id)
                _LOGGER.debug(
                    "Discovered UGT door %s (%s), adding EntityTypeSelect",
                    door.name,
                    door_id,
                )
                new_entities.append(EntityTypeSelect(data, door_id))
        if new_entities:
            async_add_entities(new_entities)

    _check_for_new_ugt_doors()
    config_entry.async_on_unload(
        data.coordinator.async_add_listener(_check_for_new_ugt_doors)
    )


def _setup_reader_selects(
    data: UnifiAccessData,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add reader selects once a reader's access-method settings are known.

    An anti-spoofing select (if the reader supports face unlock) and a PIN
    keypad layout select (if the reader exposes the PIN access method).
    """
    added_readers: set[str] = set()

    def on_reader_ready(device_id: str) -> None:
        if device_id in added_readers:
            return
        reader = data.hub.readers.get(device_id)
        if reader is None or reader.access_methods is None:
            return
        added_readers.add(device_id)
        entities: list[SelectEntity] = []
        if reader.supports_face:
            entities.append(
                FaceAntiSpoofingSelectEntity(data.hub, reader, data.coordinator)
            )
        if "pin_code" in reader.access_methods and reader.supports_method("pin_code"):
            entities.append(
                UnifiPinKeypadLayoutSelectEntity(data.hub, reader, data.coordinator)
            )
        if entities:
            async_add_entities(entities)

    data.hub.register_reader_callback(on_reader_ready)


class TemporaryLockRuleSelectEntity(UnifiAccessDoorEntity, SelectEntity):
    """Unifi Access Temporary Lock Rule Select."""

    _attr_translation_key = "door_lock_rules"

    def __init__(self, data: UnifiAccessData, door_id: str) -> None:
        """Initialize Unifi Access Door Lock Rule."""
        super().__init__(data.coordinator, data.coordinator.data[door_id])
        self._data = data
        self._attr_unique_id = f"door_lock_rule_{door_id}"
        self._update_options()

    def _update_options(self) -> None:
        """Update Door Lock Rules without duplications.

        The controller also reports rule types that are not user-selectable
        (``schedule``, ``lock_now``). The reported one is added to the option
        list so the current state stays a valid option instead of being
        rejected by Home Assistant.
        """
        lock_rule = self.coordinator.data[self.door.id].lock_rule
        self._attr_current_option = "" if lock_rule == "reset" else lock_rule

        options = [
            "",
            "keep_lock",
            "keep_unlock",
            "custom",
            "reset",
        ]

        if self._attr_current_option == "schedule":
            # A running schedule can be ended ahead of time.
            options.append("lock_early")
        if self._attr_current_option and self._attr_current_option not in options:
            options.insert(1, self._attr_current_option)

        self._attr_options = options

    async def async_select_option(self, option: str) -> None:
        """Select Door Lock Rule."""
        if not option:
            return
        await self._data.hub.async_set_lock_rule(self.door.id, option)
        if option == "reset":
            self._attr_current_option = ""
            self.async_write_ha_state()

    def _handle_coordinator_update(self) -> None:
        """Handle Unifi Access Door Lock updates from coordinator."""
        self._update_options()
        self.async_write_ha_state()


class FaceAntiSpoofingSelectEntity(UnifiAccessReaderEntity, SelectEntity):
    """Select entity for the face anti-spoofing / detection-distance combo.

    Each option is a complete, valid (anti_spoofing_level, detect_distance)
    pair, mirroring the 4-position Face Unlock slider in the UniFi UI. This
    makes invalid combinations impossible by construction.
    """

    _attr_translation_key = "face_anti_spoofing"
    _attr_options: ClassVar[list[str]] = list(ANTI_SPOOFING_COMBOS)

    def __init__(
        self,
        hub: UnifiAccessHub,
        reader: ReaderState,
        coordinator: UnifiAccessCoordinator[dict[str, DoorState]],
    ) -> None:
        """Initialize the anti-spoofing select entity."""
        super().__init__(hub, reader, coordinator)
        self._attr_unique_id = f"{reader.device_id}_face_anti_spoofing"

    async def async_added_to_hass(self) -> None:
        """Trigger an initial settings fetch when HA adds this entity."""
        await super().async_added_to_hass()
        if self.reader.access_methods is None:
            await self._hub.async_refresh_reader_settings(self.reader.device_id)

    @property
    def current_option(self) -> str | None:
        """Return the last meaningful anti-spoofing combo."""
        return self.reader.last_anti_spoofing_combo

    async def async_select_option(self, option: str) -> None:
        """Set the anti-spoofing level and detection distance as one valid pair."""
        if option not in ANTI_SPOOFING_COMBOS:
            raise HomeAssistantError(f"Invalid anti-spoofing option: {option}")
        level, distance = ANTI_SPOOFING_COMBOS[option]
        payload = {
            "access_methods": {
                "face": {
                    "anti_spoofing_level": level,
                    "detect_distance": distance,
                }
            }
        }
        try:
            await self._hub.async_update_reader_settings(self.reader.device_id, payload)
        except RuntimeError as err:
            raise HomeAssistantError(str(err)) from err
        # Keep the selection so a later refresh does not overwrite it with the
        # placeholder reported while face unlock is off, and persist it so it
        # survives a restart in that state.
        self.reader.last_anti_spoofing_combo = option
        await self._hub.async_persist_reader_settings()
        await self._hub.async_refresh_reader_settings(self.reader.device_id)

    def _handle_coordinator_update(self) -> None:
        """Handle coordinator updates."""
        self.async_write_ha_state()


class UnifiPinKeypadLayoutSelectEntity(UnifiAccessReaderEntity, SelectEntity):
    """Select for the PIN keypad layout (standard vs randomized).

    UniFi only applies this setting while the PIN access method is enabled, so
    the entity is unavailable whenever PIN is off.
    """

    _attr_translation_key = "pin_keypad_layout"
    _attr_options: ClassVar[list[str]] = list(_PIN_LAYOUT_OPTIONS)

    def __init__(
        self,
        hub: UnifiAccessHub,
        reader: ReaderState,
        coordinator: UnifiAccessCoordinator[dict[str, DoorState]],
    ) -> None:
        """Initialize the PIN keypad layout select entity."""
        super().__init__(hub, reader, coordinator)
        self._attr_unique_id = f"{reader.device_id}_pin_keypad_layout"

    @property
    def available(self) -> bool:
        """Available only while the PIN access method is enabled."""
        if not super().available:
            return False
        pin = (self.reader.access_methods or {}).get("pin_code", {})
        return pin.get("enabled") == "yes"

    @property
    def current_option(self) -> str | None:
        """Return the configured PIN keypad layout."""
        pin = (self.reader.access_methods or {}).get("pin_code", {})
        return _PIN_LAYOUT_BY_SHUFFLE.get(pin.get("pin_code_shuffle"))

    async def async_select_option(self, option: str) -> None:
        """Set the PIN keypad layout."""
        if option not in _PIN_LAYOUT_OPTIONS:
            raise HomeAssistantError(f"Invalid PIN keypad layout: {option}")
        payload = {
            "access_methods": {
                "pin_code": {"pin_code_shuffle": _PIN_LAYOUT_OPTIONS[option]}
            }
        }
        try:
            await self._hub.async_update_reader_settings(self.reader.device_id, payload)
        except RuntimeError as err:
            raise HomeAssistantError(str(err)) from err
        await self._hub.async_refresh_reader_settings(self.reader.device_id)

    def _handle_coordinator_update(self) -> None:
        """Handle coordinator updates."""
        self.async_write_ha_state()


class EntityTypeSelect(UnifiAccessDoorEntity, SelectEntity):
    """Select the HA entity type (lock / garage / gate) for a UGT door.

    Changing the type moves the door between the lock and cover/button/number
    platforms (see ``manage_door_entities``). The choice is persisted in the
    integration's Store so it survives restarts.
    """

    _attr_translation_key = "entity_type"
    _attr_options: ClassVar[list[str]] = DOOR_TYPES

    def __init__(self, data: UnifiAccessData, door_id: str) -> None:
        """Initialize EntityTypeSelect."""
        super().__init__(data.coordinator, data.coordinator.data[door_id])
        self._data = data
        self._attr_unique_id = f"{door_id}_entity_type"
        self._attr_current_option = self.door.entity_type

    async def async_select_option(self, option: str) -> None:
        """Persist the chosen entity type and update door state."""
        old_type = self.door.entity_type
        if option == old_type:
            return

        self.door.entity_type = option
        self._attr_current_option = option
        stored = {
            door_id: door_state.entity_type
            for door_id, door_state in self._data.coordinator.data.items()
        }
        await self._data.store.async_save(stored)

        _LOGGER.debug(
            "Door %s entity type changed from %s to %s",
            self.door.name,
            old_type,
            option,
        )
        self._data.coordinator.async_set_updated_data(self._data.coordinator.data)

    def _handle_coordinator_update(self) -> None:
        """Sync current option from door state on coordinator update."""
        self._attr_current_option = self.door.entity_type
        self.async_write_ha_state()
