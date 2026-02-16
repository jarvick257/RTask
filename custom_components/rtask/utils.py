"""Utility functions and classes for RTask integration."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN


def validate_and_format_datetime(dt_value: Any, context: str) -> str | None:
    """Validate and format datetime value from text input (yyyy-mm-dd hh:mm format)."""
    if dt_value is None:
        return None

    if hasattr(dt_value, "isoformat"):
        return dt_value.isoformat()
    elif isinstance(dt_value, str):
        dt_string = dt_value.strip()

        if not dt_string:
            return None

        formats_to_try = [
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%dT%H:%M:%S",
        ]

        for fmt in formats_to_try:
            try:
                parsed_dt = datetime.strptime(dt_string, fmt)
                if parsed_dt.tzinfo is None:
                    parsed_dt = parsed_dt.replace(tzinfo=dt_util.UTC)
                return parsed_dt.isoformat()
            except ValueError:
                continue

        error_msg = f"Invalid datetime format in {context}: '{dt_value}'. Expected format: yyyy-mm-dd hh:mm (e.g., '2025-09-08 16:00')"
        raise ValueError(error_msg)
    else:
        error_msg = f"Invalid datetime type in {context}: expected string, got {type(dt_value).__name__}: {dt_value}"
        raise TypeError(error_msg)


class TaskStorageManager:
    """Manages persistent storage for task completion data."""

    STORAGE_VERSION = 1
    STORAGE_KEY = f"{DOMAIN}_task_completions"

    def __init__(self, hass: HomeAssistant):
        """Initialize the storage manager."""
        self._hass = hass
        self._store: Store | None = None
        self._completions: dict[str, str] = {}

    async def initialize(self) -> None:
        """Initialize storage and load existing data."""
        if self._store is None:
            self._store = Store(self._hass, self.STORAGE_VERSION, self.STORAGE_KEY)
            stored_data = await self._store.async_load()
            self._completions = stored_data or {}

    async def get_completion(self, entry_id: str) -> str | None:
        """Get completion time for a specific entry."""
        await self.initialize()
        return self._completions.get(entry_id)

    async def set_completion(self, entry_id: str, completion_time: str) -> None:
        """Set completion time for a specific entry."""
        await self.initialize()
        self._completions[entry_id] = completion_time
        if self._store:
            await self._store.async_save(self._completions)

    async def remove_completion(self, entry_id: str) -> None:
        """Remove completion data for a specific entry."""
        await self.initialize()
        self._completions.pop(entry_id, None)
        if self._store:
            await self._store.async_save(self._completions)

    async def get_all_completions(self) -> dict[str, str]:
        """Get all completion data."""
        await self.initialize()
        return self._completions.copy()

    async def save_all_completions(self, completions: dict[str, str]) -> None:
        """Save all completion data."""
        await self.initialize()
        self._completions = completions.copy()
        if self._store:
            await self._store.async_save(self._completions)


def get_last_completed_datetime(
    hass: HomeAssistant, entry_id: str
) -> datetime | None:
    """Get the last completed timestamp from hass data."""
    return hass.data.get(DOMAIN, {}).get(entry_id, {}).get("last_completed")


def validate_duration_config(
    min_duration: int, min_unit: str, max_duration: int, max_unit: str
) -> tuple[int, int]:
    """Validate and convert duration configuration to seconds."""
    from .const import TIME_UNITS

    min_duration_seconds = min_duration * TIME_UNITS.get(min_unit, 1)
    max_duration_seconds = max_duration * TIME_UNITS.get(max_unit, 1)

    if min_duration_seconds >= max_duration_seconds:
        raise ValueError("Maximum duration must be greater than minimum duration")

    return min_duration_seconds, max_duration_seconds
