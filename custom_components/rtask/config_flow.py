"""Config flow for RTask integration."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import DOMAIN, TIME_UNIT_OPTIONS
from .utils import validate_and_format_datetime, validate_duration_config

def _build_duration_schema(
    min_duration=1,
    min_duration_unit="days",
    max_duration=2,
    max_duration_unit="days",
    last_completed="",
    include_task_name=False,
    task_name="",
) -> vol.Schema:
    """Build a duration configuration schema with optional task_name field."""
    fields: dict = {}
    if include_task_name:
        fields[vol.Required("task_name", default=task_name)] = selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
        )
    fields[vol.Required("min_duration", default=min_duration)] = selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=1, max=999999, step=1, mode=selector.NumberSelectorMode.BOX
        )
    )
    fields[vol.Required("min_duration_unit", default=min_duration_unit)] = (
        selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=TIME_UNIT_OPTIONS, mode=selector.SelectSelectorMode.DROPDOWN
            )
        )
    )
    fields[vol.Required("max_duration", default=max_duration)] = selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=1, max=999999, step=1, mode=selector.NumberSelectorMode.BOX
        )
    )
    fields[vol.Required("max_duration_unit", default=max_duration_unit)] = (
        selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=TIME_UNIT_OPTIONS, mode=selector.SelectSelectorMode.DROPDOWN
            )
        )
    )
    fields[vol.Optional("last_completed", default=last_completed)] = (
        selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
        )
    )
    return vol.Schema(fields)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for RTask."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry):
        """Create the options flow."""
        return OptionsFlowHandler()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=_build_duration_schema(include_task_name=True),
            )

        # Validate the input
        task_name = user_input.get("task_name", "").strip()
        min_duration = user_input.get("min_duration", 0)
        min_duration_unit = user_input.get("min_duration_unit", "days")
        max_duration = user_input.get("max_duration", 0)
        max_duration_unit = user_input.get("max_duration_unit", "days")
        last_completed = user_input.get("last_completed")

        if not task_name:
            errors["task_name"] = "Task name cannot be empty"

        # Validate duration configuration
        try:
            min_duration_seconds, max_duration_seconds = (
                validate_duration_config(
                    min_duration, min_duration_unit, max_duration, max_duration_unit
                )
            )
        except ValueError as e:
            errors["max_duration"] = str(e)

        # Validate datetime format
        if last_completed:
            try:
                validate_and_format_datetime(
                    last_completed, "initial config"
                )
            except (ValueError, TypeError) as e:
                errors["last_completed"] = str(e)

        if errors:
            return self.async_show_form(
                step_id="user",
                data_schema=_build_duration_schema(
                    min_duration=min_duration,
                    min_duration_unit=min_duration_unit,
                    max_duration=max_duration,
                    max_duration_unit=max_duration_unit,
                    last_completed=last_completed or "",
                    include_task_name=True,
                    task_name=task_name,
                ),
                errors=errors,
            )

        # Store durations in seconds for consistency
        validated_last_completed = None
        if last_completed:
            # We already validated this above, so this should not raise
            validated_last_completed = validate_and_format_datetime(
                last_completed, "initial config"
            )

        config_data = {
            "task_name": task_name,
            "min_duration": min_duration,
            "min_duration_unit": min_duration_unit,
            "min_duration_seconds": min_duration_seconds,
            "max_duration": max_duration,
            "max_duration_unit": max_duration_unit,
            "max_duration_seconds": max_duration_seconds,
            "last_completed": validated_last_completed,
        }

        # Create the entry with the task name as the title
        return self.async_create_entry(title=task_name, data=config_data)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for RTask."""

    def __init__(self) -> None:
        """Initialize options flow."""
        super().__init__()

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors = {}

        # Get current configuration
        current_data = self.config_entry.data

        # Get current last_completed from storage
        current_last_completed = None
        if DOMAIN in self.hass.data:
            entry_data = self.hass.data[DOMAIN].get(self.config_entry.entry_id, {})
            last_completed_dt = entry_data.get("last_completed")
            if last_completed_dt:
                # Ensure we pass a datetime object to the DateTimeSelector
                if isinstance(last_completed_dt, str):
                    try:
                        current_last_completed = datetime.fromisoformat(
                            last_completed_dt
                        )
                    except (ValueError, TypeError) as e:
                        error_msg = f"Invalid datetime string in storage: '{last_completed_dt}': {e}"
                        raise ValueError(error_msg) from e
                else:
                    current_last_completed = last_completed_dt

        if user_input is None:
            # Pre-populate form with current values
            return self.async_show_form(
                step_id="init",
                data_schema=_build_duration_schema(
                    min_duration=current_data.get("min_duration", 1),
                    min_duration_unit=current_data.get("min_duration_unit", "days"),
                    max_duration=current_data.get("max_duration", 2),
                    max_duration_unit=current_data.get("max_duration_unit", "days"),
                    last_completed=(
                        current_last_completed.strftime("%Y-%m-%d %H:%M")
                        if current_last_completed
                        else ""
                    ),
                ),
            )

        # Validate the input (same logic as config flow)
        min_duration = user_input.get("min_duration", 0)
        min_duration_unit = user_input.get("min_duration_unit", "days")
        max_duration = user_input.get("max_duration", 0)
        max_duration_unit = user_input.get("max_duration_unit", "days")
        last_completed = user_input.get("last_completed")

        # Validate duration configuration
        try:
            min_duration_seconds, max_duration_seconds = (
                validate_duration_config(
                    min_duration, min_duration_unit, max_duration, max_duration_unit
                )
            )
        except ValueError as e:
            errors["max_duration"] = str(e)

        # Validate datetime format
        if last_completed:
            try:
                validate_and_format_datetime(
                    last_completed, "options update"
                )
            except (ValueError, TypeError) as e:
                errors["last_completed"] = str(e)

        if errors:
            return self.async_show_form(
                step_id="init",
                data_schema=_build_duration_schema(
                    min_duration=min_duration,
                    min_duration_unit=min_duration_unit,
                    max_duration=max_duration,
                    max_duration_unit=max_duration_unit,
                    last_completed=last_completed or "",
                ),
                errors=errors,
            )

        # Update the config entry with new data
        new_data = {
            "task_name": current_data.get("task_name", "Unknown Task"),
            "min_duration": min_duration,
            "min_duration_unit": min_duration_unit,
            "min_duration_seconds": min_duration_seconds,
            "max_duration": max_duration,
            "max_duration_unit": max_duration_unit,
            "max_duration_seconds": max_duration_seconds,
            "last_completed": (
                validate_and_format_datetime(
                    last_completed, "options update"
                )
                if last_completed
                else None
            ),
        }

        # Update the last_completed timestamp in storage if changed
        # Convert both to comparable format for comparison
        current_comparable = None
        if current_last_completed:
            if hasattr(current_last_completed, "isoformat"):
                current_comparable = current_last_completed.isoformat()
            else:
                current_comparable = str(current_last_completed)

        new_comparable = None
        if last_completed:
            if hasattr(last_completed, "isoformat"):
                new_comparable = last_completed.isoformat()
            else:
                new_comparable = str(last_completed)

        if new_comparable != current_comparable:
            if (
                DOMAIN in self.hass.data
                and self.config_entry.entry_id in self.hass.data[DOMAIN]
            ):
                # Store datetime object in memory
                datetime_obj = None
                if last_completed:
                    if hasattr(last_completed, "isoformat"):
                        datetime_obj = last_completed
                    elif isinstance(last_completed, str):
                        try:
                            datetime_obj = datetime.fromisoformat(last_completed)
                        except (ValueError, TypeError) as e:
                            error_msg = f"Invalid datetime string during options update: '{last_completed}': {e}"
                            raise ValueError(error_msg) from e

                self.hass.data[DOMAIN][self.config_entry.entry_id][
                    "last_completed"
                ] = datetime_obj

                # Save to persistent storage using storage manager
                storage_manager = self.hass.data[DOMAIN].get("storage_manager")
                if storage_manager:
                    if datetime_obj:
                        await storage_manager.set_completion(
                            self.config_entry.entry_id, datetime_obj.isoformat()
                        )
                    else:
                        await storage_manager.remove_completion(
                            self.config_entry.entry_id
                        )

        # Persist new data into entry.data so the sensor reads updated values
        self.hass.config_entries.async_update_entry(
            self.config_entry, data=new_data
        )

        return self.async_create_entry(title="", data={})
