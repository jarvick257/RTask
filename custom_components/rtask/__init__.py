"""The RTask integration."""

from __future__ import annotations

import logging
import logging.handlers
import os
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


def setup_file_logging(hass: HomeAssistant) -> None:
    """Set up file logging for RTask."""
    # Create file handler for RTask logs
    log_file_path = os.path.join(hass.config.config_dir, "rtask.log")
    
    try:
        # Create rotating file handler (max 10MB, keep 3 backup files)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path, maxBytes=10*1024*1024, backupCount=3
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Create detailed formatter for file logs
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        # Add handler to RTask loggers
        rtask_logger = logging.getLogger(f"custom_components.{DOMAIN}")
        rtask_logger.addHandler(file_handler)
        rtask_logger.setLevel(logging.DEBUG)
        
        # Prevent duplicate logs in Home Assistant's main log
        rtask_logger.propagate = True
        
        _LOGGER.info(f"RTask file logging configured: {log_file_path}")
        
    except (OSError, PermissionError) as e:
        _LOGGER.error(f"Failed to setup file logging at {log_file_path}: {e}")
        raise

# Storage version for task completion data
STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}_task_completions"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up RTask from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Set up file logging (only once)
    if "file_logging_setup" not in hass.data[DOMAIN]:
        setup_file_logging(hass)
        hass.data[DOMAIN]["file_logging_setup"] = True

    # Initialize storage for task completion times
    if "store" not in hass.data[DOMAIN]:
        store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        hass.data[DOMAIN]["store"] = store
        # Load existing completion data
        stored_data = await store.async_load()
        hass.data[DOMAIN]["completions"] = stored_data or {}
        _LOGGER.debug(f"Loaded completion data from storage: {hass.data[DOMAIN]['completions']}")
    
    # Ensure completions dict exists even if store was already initialized
    if "completions" not in hass.data[DOMAIN]:
        store = hass.data[DOMAIN]["store"]
        stored_data = await store.async_load()
        hass.data[DOMAIN]["completions"] = stored_data or {}
        _LOGGER.debug(f"Loaded completion data from storage (fallback): {hass.data[DOMAIN]['completions']}")

    # Initialize entry data with completion time, prioritizing storage over config
    last_completed = None

    # First check stored completion time (most recent, including options flow updates)
    stored_completion = hass.data[DOMAIN]["completions"].get(entry.entry_id)
    _LOGGER.debug(f"Loading entry {entry.entry_id}: stored_completion = {stored_completion}")
    _LOGGER.debug(f"All completions in storage: {hass.data[DOMAIN]['completions']}")
    _LOGGER.debug(f"Available keys in completions: {list(hass.data[DOMAIN]['completions'].keys())}")
    if stored_completion:
        try:
            last_completed = datetime.fromisoformat(stored_completion)
            _LOGGER.debug(f"Successfully parsed stored completion time: {last_completed}")
        except (ValueError, TypeError) as e:
            error_msg = f"Invalid stored completion time '{stored_completion}' for entry {entry.entry_id}: {e}"
            _LOGGER.error(error_msg)
            raise ValueError(error_msg) from e

    # If not in storage, check if there's a manually set time in config (initial setup)
    if not last_completed:
        config_last_completed = entry.data.get("last_completed")
        _LOGGER.debug(f"No stored completion time, checking config: {config_last_completed}")
        if config_last_completed:
            try:
                last_completed = datetime.fromisoformat(config_last_completed)
                _LOGGER.debug(f"Successfully parsed config completion time: {last_completed}")
                # Save initial config time to storage
                hass.data[DOMAIN]["completions"][entry.entry_id] = config_last_completed
                store = hass.data[DOMAIN]["store"]
                await store.async_save(hass.data[DOMAIN]["completions"])
                _LOGGER.debug(f"Saved initial config time to storage")
            except (ValueError, TypeError) as e:
                error_msg = f"Invalid config completion time '{config_last_completed}' for entry {entry.entry_id}: {e}"
                _LOGGER.error(error_msg)
                raise ValueError(error_msg) from e

    hass.data[DOMAIN][entry.entry_id] = {
        "last_completed": last_completed,
    }
    
    _LOGGER.info(f"RTask entry {entry.entry_id} ({entry.data.get('task_name', 'Unknown')}) initialized with last_completed: {last_completed}")

    # Set up entry update listener
    entry.async_on_unload(entry.add_update_listener(async_update_entry))

    # Note: Custom cards in www/community/ are automatically available at /local/community/
    # No explicit registration needed in modern Home Assistant versions

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
        # Check if this is a permanent removal or just a reload
        # If the entry is being removed (not just reloaded), clean up storage
        if hasattr(entry, '_async_remove_if_unused') or entry.state.name == 'NOT_LOADED':
            # This appears to be a permanent deletion
            if entry.entry_id in hass.data[DOMAIN].get("completions", {}):
                _LOGGER.info(f"Permanently removing completion data for deleted entry {entry.entry_id}")
                hass.data[DOMAIN]["completions"].pop(entry.entry_id, None)
                # Save the updated completions to storage
                store = hass.data[DOMAIN]["store"]
                await store.async_save(hass.data[DOMAIN]["completions"])
        else:
            # This is just a reload, preserve completion data
            _LOGGER.debug(f"Temporarily unloading entry {entry.entry_id}, preserving completion data")
            
        # Always clean up runtime data
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Called when a config entry is being removed."""
    _LOGGER.info(f"Config entry {entry.entry_id} is being removed, cleaning up completion data")
    
    if DOMAIN in hass.data and "completions" in hass.data[DOMAIN]:
        if entry.entry_id in hass.data[DOMAIN]["completions"]:
            hass.data[DOMAIN]["completions"].pop(entry.entry_id, None)
            # Save the updated completions to storage
            store = hass.data[DOMAIN]["store"]
            await store.async_save(hass.data[DOMAIN]["completions"])
            _LOGGER.debug(f"Removed completion data for entry {entry.entry_id}")


async def async_update_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update a given config entry."""
    _LOGGER.info("Config entry updated for task: %s", entry.data.get("task_name"))

    # Reload the config entry to apply changes
    await hass.config_entries.async_reload(entry.entry_id)
