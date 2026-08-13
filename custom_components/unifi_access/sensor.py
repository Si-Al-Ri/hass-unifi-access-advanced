"""Platform for sensor integration."""

from datetime import UTC, datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from . import UnifiAccessConfigEntry
from .coordinator import UnifiAccessCoordinator
from .entity import UnifiAccessDoorDeviceMixin, UnifiAccessDoorEntity
from .hub import DoorState

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: UnifiAccessConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add sensor entity for passed config entry."""
    data = config_entry.runtime_data

    if data.hub.supports_door_lock_rules:
        async_add_entities(
            [
                sensor_entity(data.coordinator, door_id)
                for door_id in data.coordinator.data
                for sensor_entity in (
                    TemporaryLockRuleSensorEntity,
                    TemporaryLockRuleEndTimeSensorEntity,
                )
            ]
        )

    # "Last access" sensor — fed by access events, so WebSocket mode only.
    if not data.hub.use_polling:
        async_add_entities(
            UnifiAccessLastAccessSensor(door) for door in data.coordinator.data.values()
        )


class TemporaryLockRuleSensorEntity(UnifiAccessDoorEntity, SensorEntity):
    """Unifi Access Temporary Lock Rule Sensor."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "door_lock_rule"

    def __init__(
        self, coordinator: UnifiAccessCoordinator[dict[str, DoorState]], door_id: str
    ) -> None:
        """Initialize Unifi Access Door Lock Rule Sensor."""
        super().__init__(coordinator, coordinator.data[door_id])
        self._attr_unique_id = f"door_lock_rule_sensor_{self.door.id}"

    @property
    def native_value(self) -> str:
        """Get native value."""
        return self.door.lock_rule


class TemporaryLockRuleEndTimeSensorEntity(UnifiAccessDoorEntity, SensorEntity):
    """Unifi Access Temporary Lock Rule Sensor End Time."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "door_lock_rule_ended_time"

    def __init__(
        self, coordinator: UnifiAccessCoordinator[dict[str, DoorState]], door_id: str
    ) -> None:
        """Initialize Unifi Access Door Lock Rule Sensor End Time."""
        super().__init__(coordinator, coordinator.data[door_id])
        self._attr_unique_id = f"door_lock_rule_sensor_ended_time_{self.door.id}"

    @property
    def native_value(self) -> datetime | None:
        """Get native value."""
        if self.door.lock_rule_ended_time and int(self.door.lock_rule_ended_time) != 0:
            return datetime.fromtimestamp(int(self.door.lock_rule_ended_time), tz=UTC)
        return None


# Number of recent access events kept in the sensor's "events" attribute.
# The Lovelace card merges these across doors, so this is the upper bound for
# the card's configurable max_logs. The capture store keeps the same number of
# images per door, so every event listed here can still show its snapshot.
_MAX_HISTORY = 25

_EVENT_KEYS = (
    "actor",
    "method",
    "direction",
    "result",
    "door_name",
    "reader",
    "kind",
    "capture_id",
)


class UnifiAccessLastAccessSensor(
    UnifiAccessDoorDeviceMixin, RestoreEntity, SensorEntity
):
    """Sensor exposing the most recent access event at a door.

    Fed by a dedicated "last_access" event the hub fires alongside the
    existing "access" event — purely additive, the Door Event entity and its
    "access" event are unaffected. State is the timestamp of the last access;
    attributes carry who / method / direction / result / reader, plus an
    ``events`` list with the most recent accesses (newest first).
    """

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_translation_key = "last_access"

    def __init__(self, door: DoorState) -> None:
        """Initialize the last-access sensor."""
        self.door = door
        self._attr_unique_id = f"{door.id}_last_access"
        self._timestamp: datetime | None = None
        self._attrs: dict[str, str] = {}
        self._history: list[dict[str, str]] = []

    @property
    def native_value(self) -> datetime | None:
        """Return the timestamp of the last access."""
        return self._timestamp

    @property
    def extra_state_attributes(self) -> dict:
        """Return last-access details plus the recent-events history.

        ``events`` is returned as a shallow copy so the list held by a
        previously written State object is not mutated in place by a later
        access.
        """
        return {**self._attrs, "events": list(self._history)}

    async def async_added_to_hass(self) -> None:
        """Restore the last state and start listening for access events."""
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None:
            events = last.attributes.get("events")
            if isinstance(events, list):
                self._history = [
                    {key: str(entry.get(key, "")) for key in ("time", *_EVENT_KEYS)}
                    for entry in events
                    if isinstance(entry, dict)
                ][:_MAX_HISTORY]
            if last.state not in (None, "unknown", "unavailable"):
                self._timestamp = dt_util.parse_datetime(last.state)
                self._attrs = {
                    key: value
                    for key in _EVENT_KEYS
                    if (value := last.attributes.get(key)) is not None
                }
        self.door.add_event_listener("last_access", self._handle_access)

    async def async_will_remove_from_hass(self) -> None:
        """Stop listening for access events."""
        await super().async_will_remove_from_hass()
        self.door.remove_event_listener("last_access", self._handle_access)

    def _handle_access(self, event: str, attributes: dict[str, str]) -> None:
        """Record a last-access event from the hub.

        ``kind == "doorbell"`` is appended to the events history only — the
        sensor's main state and flat attributes keep tracking the last actual
        access (semantic of "Letzter Zutritt"). The card picks doorbell
        entries up via the events history.
        """
        now = dt_util.utcnow()
        kind = attributes.get("kind", "")
        entry = {
            "time": now.isoformat(),
            "actor": attributes.get("actor", ""),
            "method": attributes.get("method", ""),
            "direction": attributes.get("direction", ""),
            "result": attributes.get("result", ""),
            "door_name": attributes.get("door_name", self.door.name),
            "reader": attributes.get("reader", ""),
            "kind": kind,
            "capture_id": attributes.get("capture_id", ""),
        }
        if not kind:
            self._timestamp = now
            self._attrs = {k: v for k, v in entry.items() if k != "time"}
        self._history.insert(0, entry)
        del self._history[_MAX_HISTORY:]
        self.async_write_ha_state()
