"""Constants for the RTask integration."""

DOMAIN = "rtask"

# Time unit constants
TIME_UNITS = {
    "seconds": 1,
    "minutes": 60,
    "hours": 3600,
    "days": 86400,
}

TIME_UNIT_OPTIONS = [
    {"value": "seconds", "label": "Seconds"},
    {"value": "minutes", "label": "Minutes"},
    {"value": "hours", "label": "Hours"},
    {"value": "days", "label": "Days"},
]