"""Config flow for RTask integration."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import DOMAIN, TIME_UNITS, TIME_UNIT_OPTIONS


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
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
        vol.Optional("last_completed"): selector.TextSelector(
            selector.TextSelectorConfig(
                type=selector.TextSelectorType.TEXT
            )
        ),
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for RTask."""

    VERSION = 1

    def _validate_and_format_datetime(self, dt_value: Any, context: str) -> str | None:
        """Validate and format datetime value from text input (yyyy-mm-dd hh:mm format)."""

        if dt_value is None:
            return None

        if hasattr(dt_value, "isoformat"):
            # It's a datetime object
            result = dt_value.isoformat()
            return result
        elif isinstance(dt_value, str):
            dt_string = dt_value.strip()
            
            if not dt_string:
                return None

            # Try to parse the expected format: "yyyy-mm-dd hh:mm"
            formats_to_try = [
                "%Y-%m-%d %H:%M",      # "2025-09-08 16:00"
                "%Y-%m-%d %H:%M:%S",   # "2025-09-08 16:00:00"
                "%Y-%m-%d",            # "2025-09-08" (date only, defaults to 00:00)
                "%Y-%m-%dT%H:%M",      # "2025-09-08T16:00" (ISO format without seconds)
                "%Y-%m-%dT%H:%M:%S",   # "2025-09-08T16:00:00" (full ISO format)
            ]

            for fmt in formats_to_try:
                try:
                    parsed_dt = datetime.strptime(dt_string, fmt)
                    result = parsed_dt.isoformat()
                    return result
                except ValueError:
                    continue

            # If all parsing attempts fail
            error_msg = f"Invalid datetime format in {context}: '{dt_value}'. Expected format: yyyy-mm-dd hh:mm (e.g., '2025-09-08 16:00')"
            raise ValueError(error_msg)
        else:
            error_msg = f"Invalid datetime type in {context}: expected string, got {type(dt_value).__name__}: {dt_value}"
            raise TypeError(error_msg)

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
        last_completed = user_input.get("last_completed")

        if not task_name:
            errors["task_name"] = "Task name cannot be empty"

        # Convert to seconds for comparison
        min_duration_seconds = min_duration * TIME_UNITS.get(min_duration_unit, 1)
        max_duration_seconds = max_duration * TIME_UNITS.get(max_duration_unit, 1)

        if min_duration_seconds >= max_duration_seconds:
            errors["max_duration"] = (
                "Maximum duration must be greater than minimum duration"
            )

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
            "last_completed": self._validate_and_format_datetime(
                last_completed, "initial config"
            ),
        }

        # Create the entry with the task name as the title
        return self.async_create_entry(title=f"RTask: {task_name}", data=config_data)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for RTask."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        super().__init__()

    def _validate_and_format_datetime(self, dt_value: Any, context: str) -> str | None:
        """Validate and format datetime value from text input (yyyy-mm-dd hh:mm format)."""

        if dt_value is None:
            return None

        if hasattr(dt_value, "isoformat"):
            # It's a datetime object
            result = dt_value.isoformat()
            return result
        elif isinstance(dt_value, str):
            dt_string = dt_value.strip()
            
            if not dt_string:
                return None

            # Try to parse the expected format: "yyyy-mm-dd hh:mm"
            formats_to_try = [
                "%Y-%m-%d %H:%M",      # "2025-09-08 16:00"
                "%Y-%m-%d %H:%M:%S",   # "2025-09-08 16:00:00"
                "%Y-%m-%d",            # "2025-09-08" (date only, defaults to 00:00)
                "%Y-%m-%dT%H:%M",      # "2025-09-08T16:00" (ISO format without seconds)
                "%Y-%m-%dT%H:%M:%S",   # "2025-09-08T16:00:00" (full ISO format)
            ]

            for fmt in formats_to_try:
                try:
                    parsed_dt = datetime.strptime(dt_string, fmt)
                    result = parsed_dt.isoformat()
                    return result
                except ValueError:
                    continue

            # If all parsing attempts fail
            error_msg = f"Invalid datetime format in {context}: '{dt_value}'. Expected format: yyyy-mm-dd hh:mm (e.g., '2025-09-08 16:00')"
            raise ValueError(error_msg)
        else:
            error_msg = f"Invalid datetime type in {context}: expected string, got {type(dt_value).__name__}: {dt_value}"
            raise TypeError(error_msg)

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
                data_schema=vol.Schema(
                    {
                        vol.Required(
                            "task_name", default=current_data.get("task_name", "")
                        ): selector.TextSelector(
                            selector.TextSelectorConfig(
                                type=selector.TextSelectorType.TEXT
                            )
                        ),
                        vol.Required(
                            "min_duration", default=current_data.get("min_duration", 1)
                        ): selector.NumberSelector(
                            selector.NumberSelectorConfig(
                                min=1,
                                max=999999,
                                step=1,
                                mode=selector.NumberSelectorMode.BOX,
                            )
                        ),
                        vol.Required(
                            "min_duration_unit",
                            default=current_data.get("min_duration_unit", "days"),
                        ): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                options=TIME_UNIT_OPTIONS,
                                mode=selector.SelectSelectorMode.DROPDOWN,
                            )
                        ),
                        vol.Required(
                            "max_duration", default=current_data.get("max_duration", 7)
                        ): selector.NumberSelector(
                            selector.NumberSelectorConfig(
                                min=1,
                                max=999999,
                                step=1,
                                mode=selector.NumberSelectorMode.BOX,
                            )
                        ),
                        vol.Required(
                            "max_duration_unit",
                            default=current_data.get("max_duration_unit", "days"),
                        ): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                options=TIME_UNIT_OPTIONS,
                                mode=selector.SelectSelectorMode.DROPDOWN,
                            )
                        ),
                        vol.Optional(
                            "last_completed", 
                            default=current_last_completed.strftime("%Y-%m-%d %H:%M") if current_last_completed else ""
                        ): selector.TextSelector(
                            selector.TextSelectorConfig(
                                type=selector.TextSelectorType.TEXT
                            )
                        ),
                    }
                ),
            )

        # Validate the input (same logic as config flow)
        task_name = user_input.get("task_name", "").strip()
        min_duration = user_input.get("min_duration", 0)
        min_duration_unit = user_input.get("min_duration_unit", "days")
        max_duration = user_input.get("max_duration", 0)
        max_duration_unit = user_input.get("max_duration_unit", "days")
        last_completed = user_input.get("last_completed")


        if not task_name:
            errors["task_name"] = "Task name cannot be empty"

        # Convert to seconds for comparison
        min_duration_seconds = min_duration * TIME_UNITS.get(min_duration_unit, 1)
        max_duration_seconds = max_duration * TIME_UNITS.get(max_duration_unit, 1)

        if min_duration_seconds >= max_duration_seconds:
            errors["max_duration"] = (
                "Maximum duration must be greater than minimum duration"
            )

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
            "last_completed": self._validate_and_format_datetime(
                last_completed, "options update"
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
                datetime_obj = (
                    current_last_completed  # Start with current value as fallback
                )
                if last_completed:
                    if hasattr(last_completed, "isoformat"):
                        datetime_obj = last_completed
                    elif isinstance(last_completed, str):
                        try:
                            datetime_obj = datetime.fromisoformat(last_completed)
                        except (ValueError, TypeError) as e:
                            error_msg = f"Invalid datetime string during options update: '{last_completed}': {e}"
                            raise ValueError(error_msg) from e
                elif last_completed is None:
                    # Explicitly setting to None, so clear it
                    datetime_obj = None

                self.hass.data[DOMAIN][self.config_entry.entry_id][
                    "last_completed"
                ] = datetime_obj

                # Save to persistent storage
                if datetime_obj:
                    # Validate and convert to ISO format string
                    if hasattr(datetime_obj, "isoformat"):
                        iso_string = datetime_obj.isoformat()
                    elif isinstance(datetime_obj, str):
                        # Re-validate string format before storing
                        try:
                            parsed = datetime.fromisoformat(datetime_obj)
                            iso_string = parsed.isoformat()
                        except (ValueError, TypeError) as e:
                            error_msg = f"Cannot store invalid datetime string '{datetime_obj}': {e}"
                            raise ValueError(error_msg) from e
                    else:
                        error_msg = f"Cannot store datetime of unexpected type {type(datetime_obj).__name__}: {datetime_obj}"
                        raise TypeError(error_msg)

                    self.hass.data[DOMAIN]["completions"][
                        self.config_entry.entry_id
                    ] = iso_string
                else:
                    self.hass.data[DOMAIN]["completions"].pop(
                        self.config_entry.entry_id, None
                    )

                store = self.hass.data[DOMAIN]["store"]
                await store.async_save(self.hass.data[DOMAIN]["completions"])

        # Update the title if the task name changed
        title = f"RTask: {task_name}"

        return self.async_create_entry(title=title, data=new_data)
