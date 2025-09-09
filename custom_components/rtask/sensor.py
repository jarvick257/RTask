"""Platform for sensor integration."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    DOMAIN,
    DEFAULT_MIN_DURATION_SECONDS,
    DEFAULT_MAX_DURATION_SECONDS,
    UPDATE_INTERVAL_MINUTES,
    UPDATE_INTERVAL_SECONDS,
    SENSOR_STATE_NEVER_DONE,
    SENSOR_STATE_DONE,
    SENSOR_STATE_DUE,
    SENSOR_STATE_OVERDUE,
)
from .utils import TaskDataValidator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    async_add_entities([RTaskSensor(hass, config_entry)])


class RTaskSensor(SensorEntity):
    """Representation of a RTask sensor."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        self._hass = hass
        self._config_entry = config_entry
        task_name = config_entry.data.get("task_name", "Unknown Task")
        self._attr_name = f"RTask {task_name}"
        self._attr_unique_id = (
            f"{DOMAIN}_{config_entry.entry_id}_{task_name.lower().replace(' ', '_')}"
        )
        self._attr_should_poll = False

    @property
    def native_value(self) -> str:
        """Return the native value of the sensor."""
        last_completed = self._get_last_completed()
        if last_completed is None:
            return SENSOR_STATE_NEVER_DONE

        config_data = self._config_entry.data
        min_seconds = TaskDataValidator.get_config_value_safe(
            config_data, "min_duration_seconds", DEFAULT_MIN_DURATION_SECONDS
        )
        max_seconds = TaskDataValidator.get_config_value_safe(
            config_data, "max_duration_seconds", DEFAULT_MAX_DURATION_SECONDS
        )

        seconds_since = (datetime.now() - last_completed).total_seconds()

        if seconds_since < min_seconds:
            return SENSOR_STATE_DONE
        elif seconds_since <= max_seconds:
            return SENSOR_STATE_DUE
        else:
            return SENSOR_STATE_OVERDUE

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        config_data = self._config_entry.data
        last_completed = self._get_last_completed()

        attributes = {
            "task_name": TaskDataValidator.get_config_value_safe(
                config_data, "task_name", "Unknown"
            ),
            "min_duration": TaskDataValidator.get_config_value_safe(
                config_data, "min_duration", 1
            ),
            "min_duration_unit": TaskDataValidator.get_config_value_safe(
                config_data, "min_duration_unit", "days"
            ),
            "max_duration": TaskDataValidator.get_config_value_safe(
                config_data, "max_duration", 7
            ),
            "max_duration_unit": TaskDataValidator.get_config_value_safe(
                config_data, "max_duration_unit", "days"
            ),
            "min_duration_seconds": TaskDataValidator.get_config_value_safe(
                config_data, "min_duration_seconds", DEFAULT_MIN_DURATION_SECONDS
            ),
            "max_duration_seconds": TaskDataValidator.get_config_value_safe(
                config_data, "max_duration_seconds", DEFAULT_MAX_DURATION_SECONDS
            ),
            "last_completed": last_completed.isoformat() if last_completed else None,
        }

        if last_completed:
            seconds_since = (datetime.now() - last_completed).total_seconds()
            attributes["seconds_since_completed"] = int(seconds_since)
            attributes["minutes_since_completed"] = int(seconds_since / 60)
            attributes["hours_since_completed"] = int(seconds_since / 3600)
            attributes["days_since_completed"] = int(seconds_since / 86400)

            # Add time until due/overdue for better visibility
            min_seconds = TaskDataValidator.get_config_value_safe(
                config_data, "min_duration_seconds", DEFAULT_MIN_DURATION_SECONDS
            )
            max_seconds = TaskDataValidator.get_config_value_safe(
                config_data, "max_duration_seconds", DEFAULT_MAX_DURATION_SECONDS
            )

            if seconds_since < min_seconds:
                attributes["seconds_until_due"] = int(min_seconds - seconds_since)
            elif seconds_since < max_seconds:
                attributes["seconds_until_overdue"] = int(max_seconds - seconds_since)
            else:
                attributes["seconds_overdue"] = int(seconds_since - max_seconds)

        return attributes

    def _get_last_completed(self) -> datetime | None:
        """Get the last completed timestamp from hass data with proper error handling."""
        return TaskDataValidator.get_last_completed_datetime(
            self._hass, self._config_entry.entry_id
        )

    async def async_mark_done(self) -> None:
        """Mark this task as completed."""
        await self._hass.services.async_call(
            DOMAIN,
            "mark_done",
            {"entity_id": self.entity_id},
        )

    async def async_added_to_hass(self) -> None:
        """Register for state changes."""
        await super().async_added_to_hass()

        @callback
        def _async_update_state(*args):
            """Update the sensor state."""
            self.async_write_ha_state()

        @callback
        def _async_task_completed(event):
            """Handle task completion event."""
            if event.data.get("entity_id") == self.entity_id:
                self.async_write_ha_state()

        # Listen for task completion events
        self._hass.bus.async_listen("rtask_task_completed", _async_task_completed)

        # Schedule regular updates to check status (every 5 minutes for performance)
        async_track_time_interval(
            self._hass,
            _async_update_state,
            timedelta(minutes=UPDATE_INTERVAL_MINUTES, seconds=UPDATE_INTERVAL_SECONDS),
        )
