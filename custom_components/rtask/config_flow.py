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

    @staticmethod
    def async_get_options_flow(config_entry):
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)

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


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for RTask."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors = {}
        
        # Get current configuration
        current_data = self.config_entry.data
        
        if user_input is None:
            # Pre-populate form with current values
            return self.async_show_form(
                step_id="init",
                data_schema=vol.Schema({
                    vol.Required("task_name", default=current_data.get("task_name", "")): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                    ),
                    vol.Required("min_duration", default=current_data.get("min_duration", 1)): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1, max=999999, step=1, mode=selector.NumberSelectorMode.BOX
                        )
                    ),
                    vol.Required("min_duration_unit", default=current_data.get("min_duration_unit", "days")): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=TIME_UNIT_OPTIONS, mode=selector.SelectSelectorMode.DROPDOWN
                        )
                    ),
                    vol.Required("max_duration", default=current_data.get("max_duration", 7)): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1, max=999999, step=1, mode=selector.NumberSelectorMode.BOX
                        )
                    ),
                    vol.Required("max_duration_unit", default=current_data.get("max_duration_unit", "days")): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=TIME_UNIT_OPTIONS, mode=selector.SelectSelectorMode.DROPDOWN
                        )
                    ),
                })
            )

        # Validate the input (same logic as config flow)
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
            return self.async_show_form(step_id="init", errors=errors)
        
        # Update the config entry with new data
        new_data = {
            "task_name": task_name,
            "min_duration": min_duration,
            "min_duration_unit": min_duration_unit,
            "min_duration_seconds": min_duration_seconds,
            "max_duration": max_duration,
            "max_duration_unit": max_duration_unit,
            "max_duration_seconds": max_duration_seconds,
        }

        # Update the title if the task name changed
        title = f"RTask: {task_name}"
        
        return self.async_create_entry(title=title, data=new_data)