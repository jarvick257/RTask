"""Constants for the RTask integration."""

DOMAIN = "rtask"

# Time unit constants
TIME_UNITS = {
    "seconds": 1,
    "hours": 3600,
    "days": 86400,
}

TIME_UNIT_OPTIONS = [
    {"value": "seconds", "label": "Seconds"},
    {"value": "hours", "label": "Hours"},
    {"value": "days", "label": "Days"},
]

# Default duration constants
DEFAULT_MIN_DURATION_SECONDS = 86400  # 1 day
DEFAULT_MAX_DURATION_SECONDS = 604800  # 7 days

# Update interval for sensor state checks
UPDATE_INTERVAL_MINUTES = 0
UPDATE_INTERVAL_SECONDS = 1

# Sensor state constants
SENSOR_STATE_NEVER_DONE = "Never Done"
SENSOR_STATE_DONE = "Done"
SENSOR_STATE_DUE = "Due"
SENSOR_STATE_OVERDUE = "Overdue"
