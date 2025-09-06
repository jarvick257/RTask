"""The RTask integration."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.storage import Store

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

# Storage version for task completion data
STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}_task_completions"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up RTask from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Initialize storage for task completion times
    if "store" not in hass.data[DOMAIN]:
        store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        hass.data[DOMAIN]["store"] = store
        # Load existing completion data
        stored_data = await store.async_load()
        hass.data[DOMAIN]["completions"] = stored_data or {}
    
    # Initialize entry data with stored completion time if available
    stored_completion = hass.data[DOMAIN]["completions"].get(entry.entry_id)
    last_completed = None
    if stored_completion:
        try:
            last_completed = datetime.fromisoformat(stored_completion)
        except (ValueError, TypeError):
            _LOGGER.warning("Invalid stored completion time for entry %s", entry.entry_id)
    
    hass.data[DOMAIN][entry.entry_id] = {
        "last_completed": last_completed,
    }
    
    # Set up entry update listener
    entry.async_on_unload(entry.add_update_listener(async_update_entry))

    # Register the custom card resource (only do this once)
    if "rtask_card_registered" not in hass.data[DOMAIN]:
        try:
            # Register the card resource path
            await hass.http.async_register_static_path(
                "/local/community/rtask-card",
                hass.config.path("www/community/rtask-card"),
                cache_headers=False
            )
            hass.data[DOMAIN]["rtask_card_registered"] = True
            _LOGGER.info("RTask card resource registered at /local/community/rtask-card")
        except Exception as err:
            _LOGGER.warning("Could not register RTask card resource: %s", err)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register the mark_done service
    async def handle_mark_done(call: ServiceCall) -> None:
        """Handle the mark_done service call."""
        entity_id = call.data.get("entity_id")
        
        if not entity_id:
            _LOGGER.error("No entity_id provided for mark_done service")
            return

        # Find the config entry for this entity
        entity_registry = er.async_get(hass)
        entity_entry = entity_registry.async_get(entity_id)
        
        if not entity_entry or entity_entry.platform != DOMAIN:
            _LOGGER.error("Entity %s not found or not an RTask entity", entity_id)
            return

        # Update the last completed time
        config_entry_id = entity_entry.config_entry_id
        if config_entry_id in hass.data[DOMAIN]:
            now = datetime.now()
            hass.data[DOMAIN][config_entry_id]["last_completed"] = now
            
            # Save to persistent storage
            hass.data[DOMAIN]["completions"][config_entry_id] = now.isoformat()
            store = hass.data[DOMAIN]["store"]
            await store.async_save(hass.data[DOMAIN]["completions"])
            
            _LOGGER.info("Marked task %s as done at %s", entity_id, now)
            
            # Force state update by firing completion event
            hass.bus.async_fire("rtask_task_completed", {"entity_id": entity_id})

    hass.services.async_register(DOMAIN, "mark_done", handle_mark_done)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        # Clean up stored completion data for this entry
        if entry.entry_id in hass.data[DOMAIN].get("completions", {}):
            hass.data[DOMAIN]["completions"].pop(entry.entry_id, None)
            # Save the updated completions to storage
            store = hass.data[DOMAIN]["store"]
            await store.async_save(hass.data[DOMAIN]["completions"])
        
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok


async def async_update_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update a given config entry."""
    _LOGGER.info("Config entry updated for task: %s", entry.data.get("task_name"))
    
    # Reload the config entry to apply changes
    await hass.config_entries.async_reload(entry.entry_id)