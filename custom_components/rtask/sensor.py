"""Platform for sensor integration."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

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
from .utils import get_last_completed_datetime


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
        self._attr_should_poll = False
        
    @property 
    def name(self) -> str:
        """Return the name of the sensor."""
        task_name = self._config_entry.data.get("task_name", "Unknown Task")
        return f"RTask {task_name}"
        
    @property
    def unique_id(self) -> str:
        """Return the unique id of the sensor.""" 
        # Use entry_id to ensure stable unique_id even when task name changes
        return f"{DOMAIN}_{self._config_entry.entry_id}"

    @property
    def native_value(self) -> str:
        """Return the native value of the sensor."""
        last_completed = self._get_last_completed()
        if last_completed is None:
            return SENSOR_STATE_NEVER_DONE

        config_data = self._config_entry.data
        min_seconds = config_data.get("min_duration_seconds", DEFAULT_MIN_DURATION_SECONDS)
        max_seconds = config_data.get("max_duration_seconds", DEFAULT_MAX_DURATION_SECONDS)

        seconds_since = (dt_util.utcnow() - last_completed).total_seconds()

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
            "task_name": config_data.get("task_name", "Unknown"),
            "min_duration": config_data.get("min_duration", 1),
            "min_duration_unit": config_data.get("min_duration_unit", "days"),
            "max_duration": config_data.get("max_duration", 7),
            "max_duration_unit": config_data.get("max_duration_unit", "days"),
            "min_duration_seconds": config_data.get("min_duration_seconds", DEFAULT_MIN_DURATION_SECONDS),
            "max_duration_seconds": config_data.get("max_duration_seconds", DEFAULT_MAX_DURATION_SECONDS),
            "last_completed": last_completed.isoformat() if last_completed else None,
        }

        if last_completed:
            seconds_since = (dt_util.utcnow() - last_completed).total_seconds()
            attributes["seconds_since_completed"] = int(seconds_since)
            attributes["minutes_since_completed"] = int(seconds_since / 60)
            attributes["hours_since_completed"] = int(seconds_since / 3600)
            attributes["days_since_completed"] = int(seconds_since / 86400)

            # Add time until due/overdue for better visibility
            min_seconds = config_data.get("min_duration_seconds", DEFAULT_MIN_DURATION_SECONDS)
            max_seconds = config_data.get("max_duration_seconds", DEFAULT_MAX_DURATION_SECONDS)

            if seconds_since < min_seconds:
                attributes["seconds_until_due"] = int(min_seconds - seconds_since)
            elif seconds_since < max_seconds:
                attributes["seconds_until_overdue"] = int(max_seconds - seconds_since)
            else:
                attributes["seconds_overdue"] = int(seconds_since - max_seconds)

        return attributes

    def _get_last_completed(self) -> datetime | None:
        """Get the last completed timestamp from hass data with proper error handling."""
        return get_last_completed_datetime(
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
        unsub_event = self._hass.bus.async_listen(
            "rtask_task_completed", _async_task_completed
        )
        self.async_on_remove(unsub_event)

        # Schedule regular updates to check status (every 5 minutes for performance)
        unsub_interval = async_track_time_interval(
            self._hass,
            _async_update_state,
            timedelta(minutes=UPDATE_INTERVAL_MINUTES, seconds=UPDATE_INTERVAL_SECONDS),
        )
        self.async_on_remove(unsub_interval)
