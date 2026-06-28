"""Konstanten für GFS Backup Manager."""

DOMAIN = "gfs_backup_manager"
ADDON_SLUG = "b9d02817_gfs_backup"
ADDON_NAME = "GFS Backup Manager"
ADDON_API_PORT = 8099
ADDON_WS_PORT = 8098

SCAN_INTERVAL_SECONDS = 60

BACKUP_TYPES = ["daily", "weekly", "monthly", "yearly"]

BACKUP_TYPE_LABELS = {
    "daily": "Täglich",
    "weekly": "Wöchentlich",
    "monthly": "Monatlich",
    "yearly": "Jährlich",
}

BACKUP_PREFIXES = {
    "daily": "HA-Daily-",
    "weekly": "HA-Weekly-",
    "monthly": "HA-Monthly-",
    "yearly": "HA-Yearly-",
}
