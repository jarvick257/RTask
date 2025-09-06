"""Config flow for RTask integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import DOMAIN, TIME_UNITS, TIME_UNIT_OPTIONS

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required("task_name"): selector.TextSelector(
        selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
    ),
    vol.Required("min_duration"): selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=1, max=999999, step=1, mode=selector.NumberSelectorMode.BOX
        )
    ),
    vol.Required("min_duration_unit", default="days"): selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=TIME_UNIT_OPTIONS, mode=selector.SelectSelectorMode.DROPDOWN
        )
    ),
    vol.Required("max_duration"): selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=1, max=999999, step=1, mode=selector.NumberSelectorMode.BOX
        )
    ),
    vol.Required("max_duration_unit", default="days"): selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=TIME_UNIT_OPTIONS, mode=selector.SelectSelectorMode.DROPDOWN
        )
    ),
})


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for RTask."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}
        
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        # Validate the input
        task_name = user_input.get("task_name", "").strip()
        min_duration = user_input.get("min_duration", 0)
        min_duration_unit = user_input.get("min_duration_unit", "days")
        max_duration = user_input.get("max_duration", 0)
        max_duration_unit = user_input.get("max_duration_unit", "days")

        if not task_name:
            errors["task_name"] = "Task name cannot be empty"
        
        # Convert to seconds for comparison
        min_duration_seconds = min_duration * TIME_UNITS.get(min_duration_unit, 1)
        max_duration_seconds = max_duration * TIME_UNITS.get(max_duration_unit, 1)
        
        if min_duration_seconds >= max_duration_seconds:
            errors["max_duration"] = "Maximum duration must be greater than minimum duration"

        if errors:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
            )

        # Store durations in seconds for consistency
        config_data = {
            "task_name": task_name,
            "min_duration": min_duration,
            "min_duration_unit": min_duration_unit,
            "min_duration_seconds": min_duration_seconds,
            "max_duration": max_duration,
            "max_duration_unit": max_duration_unit,
            "max_duration_seconds": max_duration_seconds,
        }

        # Create the entry with the task name as the title
        return self.async_create_entry(title=f"RTask: {task_name}", data=config_data)