"""Platform for number (interval) integration."""

from homeassistant.components.number import RestoreNumber
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import UnifiAccessConfigEntry
from .const import DOMAIN, DOOR_TYPE_GARAGE, DOOR_TYPE_GATE
from .entity import manage_door_entities
from .hub import DoorState

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: UnifiAccessConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add number entity for passed config entry."""
    data = config_entry.runtime_data

    if data.hub.supports_door_lock_rules:
        async_add_entities(
            [
                TemporaryLockRuleIntervalNumberEntity(door)
                for door in data.coordinator.data.values()
            ]
        )

    # Open/close travel-time config for garage/gate covers.
    manage_door_entities(
        config_entry,
        data.coordinator,
        async_add_entities,
        lambda door: door.entity_type in (DOOR_TYPE_GARAGE, DOOR_TYPE_GATE),
        lambda door_id: [
            DoorOpenTimeNumberEntity(data.coordinator.data[door_id]),
            DoorCloseTimeNumberEntity(data.coordinator.data[door_id]),
        ],
    )


class TemporaryLockRuleIntervalNumberEntity(RestoreNumber):
    """Unifi Access Temporary Lock Rule Interval."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False
    _attr_has_entity_name = True
    _attr_native_step = 1
    _attr_should_poll = False
    _attr_translation_key = "door_lock_rule_interval"

    def __init__(self, door: DoorState) -> None:
        """Initialize Unifi Access Door Lock Rule Interval."""
        super().__init__()
        self.door = door
        self._attr_unique_id = f"door_lock_rule_interval_{self.door.id}"
        self._attr_native_value = 10
        self._attr_native_min_value = 1
        self._attr_native_max_value = 480

    @property
    def device_info(self) -> DeviceInfo:
        """Get Unifi Access Door Lock device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.door.id)},
            name=self.door.name,
            model=self.door.hub_type,
            manufacturer="Unifi",
        )

    async def async_added_to_hass(self) -> None:
        """Restore the last configured interval and apply it to the door."""
        await super().async_added_to_hass()
        last = await self.async_get_last_number_data()
        if last and last.native_value is not None:
            self._attr_native_value = last.native_value
        if self.native_value:
            self.door.lock_rule_interval = int(self.native_value)

    async def async_set_native_value(self, value: float) -> None:
        """Select Door Lock Rule Interval (in minutes)."""
        self._attr_native_value = value
        self.door.lock_rule_interval = int(value)


class _DoorTravelTimeNumberEntity(RestoreNumber):
    """Base for the garage/gate open/close travel-time config entities."""

    _attr_has_entity_name = True
    _attr_native_step = 1
    _attr_native_min_value = 0
    _attr_native_max_value = 120
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, door: DoorState) -> None:
        """Initialize the travel-time entity."""
        super().__init__()
        self.door = door
        self._attr_native_value = self._current()

    def _current(self) -> int:
        """Return the door's current value for this timer."""
        raise NotImplementedError

    def _apply(self, value: int) -> None:
        """Store the value back onto the door state."""
        raise NotImplementedError

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.door.id)},
            name=self.door.name,
            model=self.door.hub_type,
            manufacturer="Unifi",
        )

    async def async_added_to_hass(self) -> None:
        """Restore last value."""
        await super().async_added_to_hass()
        last = await self.async_get_last_number_data()
        if last and last.native_value is not None:
            self._attr_native_value = last.native_value
            self._apply(int(last.native_value))

    async def async_set_native_value(self, value: float) -> None:
        """Set the travel time."""
        self._attr_native_value = value
        self._apply(int(value))


class DoorOpenTimeNumberEntity(_DoorTravelTimeNumberEntity):
    """Configures the opening timeout for a garage/gate cover."""

    _attr_translation_key = "door_open_time"

    def __init__(self, door: DoorState) -> None:
        """Initialize Door Open Time."""
        super().__init__(door)
        self._attr_unique_id = f"door_open_time_{door.id}"

    def _current(self) -> int:
        return self.door.open_time

    def _apply(self, value: int) -> None:
        self.door.open_time = value


class DoorCloseTimeNumberEntity(_DoorTravelTimeNumberEntity):
    """Configures the closing timeout for a garage/gate cover."""

    _attr_translation_key = "door_close_time"

    def __init__(self, door: DoorState) -> None:
        """Initialize Door Close Time."""
        super().__init__(door)
        self._attr_unique_id = f"door_close_time_{door.id}"

    def _current(self) -> int:
        return self.door.close_time

    def _apply(self, value: int) -> None:
        self.door.close_time = value
