"""Konstanten für GFS Backup Manager."""

DOMAIN = "gfs_backup_manager"
ADDON_SLUG = "b9d02817_gfs_backup"
ADDON_NAME = "GFS Backup Manager"
# Addon läuft auf dem HA-Host, Port 8099 ist nach außen freigegeben
ADDON_API_PORT = 8099

SCAN_INTERVAL_SECONDS = 60

# Backup-Typen
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

# stdin Befehle ans Addon
CMD_TRIGGER_DAILY = "trigger_daily"
CMD_TRIGGER_WEEKLY = "trigger_weekly"
CMD_TRIGGER_MONTHLY = "trigger_monthly"
CMD_TRIGGER_YEARLY = "trigger_yearly"
CMD_DELETE_LAST_LOCAL = "delete_last_local"
CMD_DELETE_LAST_NAS_DAILY = "delete_last_nas_daily"
CMD_DELETE_LAST_NAS_WEEKLY = "delete_last_nas_weekly"
CMD_DELETE_LAST_NAS_MONTHLY = "delete_last_nas_monthly"
CMD_DELETE_LAST_NAS_YEARLY = "delete_last_nas_yearly"
