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
