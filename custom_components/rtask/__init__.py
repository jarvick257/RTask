"""The RTask integration."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry as er
from homeassistant.exceptions import ServiceValidationError

from .const import DOMAIN
from .utils import TaskStorageManager, DateTimeValidator

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up RTask from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Initialize storage manager if not exists
    if "storage_manager" not in hass.data[DOMAIN]:
        storage_manager = TaskStorageManager(hass)
        await storage_manager.initialize()
        hass.data[DOMAIN]["storage_manager"] = storage_manager
    else:
        storage_manager = hass.data[DOMAIN]["storage_manager"]

    # Initialize entry data with completion time, prioritizing storage over config
    last_completed = None

    # First check stored completion time (most recent, including options flow updates)
    stored_completion = await storage_manager.get_completion(entry.entry_id)
    if stored_completion:
        try:
            last_completed = datetime.fromisoformat(stored_completion)
        except (ValueError, TypeError) as e:
            error_msg = f"Invalid stored completion time '{stored_completion}' for entry {entry.entry_id}: {e}"
            raise ValueError(error_msg) from e

    # If not in storage, check if there's a manually set time in config (initial setup)
    if not last_completed:
        config_last_completed = entry.data.get("last_completed")
        if config_last_completed:
            try:
                last_completed = datetime.fromisoformat(config_last_completed)
                # Save initial config time to storage
                await storage_manager.set_completion(
                    entry.entry_id, config_last_completed
                )
            except (ValueError, TypeError) as e:
                error_msg = f"Invalid config completion time '{config_last_completed}' for entry {entry.entry_id}: {e}"
                raise ValueError(error_msg) from e

    hass.data[DOMAIN][entry.entry_id] = {
        "last_completed": last_completed,
    }

    # Set up entry update listener
    entry.async_on_unload(entry.add_update_listener(async_update_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register the mark_done service
    async def handle_mark_done(call: ServiceCall) -> None:
        """Handle the mark_done service call."""
        entity_id = call.data.get("entity_id")

        if not entity_id:
            raise ServiceValidationError("No entity_id provided for mark_done service")

        # Find the config entry for this entity
        entity_registry = er.async_get(hass)
        entity_entry = entity_registry.async_get(entity_id)

        if not entity_entry or entity_entry.platform != DOMAIN:
            raise ServiceValidationError(
                f"Entity {entity_id} not found or not an RTask entity"
            )

        # Update the last completed time
        config_entry_id = entity_entry.config_entry_id
        if config_entry_id in hass.data[DOMAIN]:
            now = datetime.now()
            hass.data[DOMAIN][config_entry_id]["last_completed"] = now

            # Save to persistent storage using storage manager
            storage_manager = hass.data[DOMAIN]["storage_manager"]
            await storage_manager.set_completion(config_entry_id, now.isoformat())

            # Force state update by firing completion event
            hass.bus.async_fire("rtask_task_completed", {"entity_id": entity_id})

    hass.services.async_register(DOMAIN, "mark_done", handle_mark_done)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        # Check if this is a permanent removal or just a reload
        # If the entry is being removed (not just reloaded), clean up storage
        if (
            hasattr(entry, "_async_remove_if_unused")
            or entry.state.name == "NOT_LOADED"
        ):
            # This appears to be a permanent deletion
            storage_manager = hass.data[DOMAIN].get("storage_manager")
            if storage_manager:
                await storage_manager.remove_completion(entry.entry_id)
        else:
            # This is just a reload, preserve completion data
            pass

        # Always clean up runtime data
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Called when a config entry is being removed."""
    if DOMAIN in hass.data:
        storage_manager = hass.data[DOMAIN].get("storage_manager")
        if storage_manager:
            await storage_manager.remove_completion(entry.entry_id)


async def async_update_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update a given config entry."""
    # Recalculate duration seconds based on updated units
    from .utils import TaskDataValidator
    
    config_data = dict(entry.data)
    
    # Recalculate duration seconds if duration values are present
    min_duration = config_data.get("min_duration")
    min_duration_unit = config_data.get("min_duration_unit")
    max_duration = config_data.get("max_duration")
    max_duration_unit = config_data.get("max_duration_unit")
    
    if all([min_duration, min_duration_unit, max_duration, max_duration_unit]):
        try:
            min_duration_seconds, max_duration_seconds = (
                TaskDataValidator.validate_duration_config(
                    min_duration, min_duration_unit, max_duration, max_duration_unit
                )
            )
            config_data["min_duration_seconds"] = min_duration_seconds
            config_data["max_duration_seconds"] = max_duration_seconds
            
            # Update the config entry with recalculated values
            hass.config_entries.async_update_entry(
                entry, data=config_data
            )
        except ValueError:
            # If validation fails, just proceed with reload
            pass
    
    # Reload the config entry to apply changes
    await hass.config_entries.async_reload(entry.entry_id)
