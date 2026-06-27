"""Sensoren für GFS Backup Manager."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, BACKUP_TYPE_LABELS
from .coordinator import GFSBackupCoordinator

_LOGGER = logging.getLogger(__name__)

DEVICE_INFO = DeviceInfo(
    identifiers={(DOMAIN, "gfs_backup_manager")},
    name="GFS Backup Manager",
    manufacturer="Max6025",
    model="GFS Backup Addon",
)


@dataclass
class GFSSensorDescription(SensorEntityDescription):
    backup_type: str = ""
    value_key: str = ""


SENSOR_TYPES: list[GFSSensorDescription] = []

for btype, label in BACKUP_TYPE_LABELS.items():
    SENSOR_TYPES += [
        GFSSensorDescription(
            key=f"{btype}_status",
            name=f"GFS {label} – Status",
            icon="mdi:shield-check",
            backup_type=btype,
            value_key="status",
        ),
        GFSSensorDescription(
            key=f"{btype}_last_date",
            name=f"GFS {label} – Letztes Backup",
            icon="mdi:calendar-clock",
            backup_type=btype,
            value_key="last_date",
        ),
        GFSSensorDescription(
            key=f"{btype}_next",
            name=f"GFS {label} – Nächstes Backup",
            icon="mdi:calendar-arrow-right",
            backup_type=btype,
            value_key="next_backup",
        ),
        GFSSensorDescription(
            key=f"{btype}_count",
            name=f"GFS {label} – Anzahl",
            icon="mdi:counter",
            backup_type=btype,
            value_key="count",
            native_unit_of_measurement="Backups",
        ),
        GFSSensorDescription(
            key=f"{btype}_size",
            name=f"GFS {label} – Größe",
            icon="mdi:harddisk",
            backup_type=btype,
            value_key="last_size_mb",
            native_unit_of_measurement="MB",
        ),
    ]

# Addon-Status Sensor
SENSOR_TYPES.append(
    GFSSensorDescription(
        key="addon_running",
        name="GFS Backup Addon – Status",
        icon="mdi:puzzle",
        backup_type="",
        value_key="addon_running",
    )
)

# Prozess-Status Sensor
SENSOR_TYPES.append(
    GFSSensorDescription(
        key="process_status",
        name="GFS Backup – Aktueller Vorgang",
        icon="mdi:backup-restore",
        backup_type="",
        value_key="process_status",
    )
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: GFSBackupCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        GFSBackupSensor(coordinator, description)
        for description in SENSOR_TYPES
    )


class GFSBackupSensor(CoordinatorEntity, SensorEntity):
    """GFS Backup Sensor."""

    entity_description: GFSSensorDescription

    def __init__(self, coordinator: GFSBackupCoordinator, description: GFSSensorDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"gfs_backup_{description.key}"
        self._attr_device_info = DEVICE_INFO

    @property
    def native_value(self):
        data = self.coordinator.data
        if not data:
            return None

        # Addon-Status
        if self.entity_description.value_key == "addon_running":
            running = data.get("addon_running", False)
            return "Läuft" if running else "Gestoppt"

        # Prozess-Status
        if self.entity_description.value_key == "process_status":
            phase = data.get("phase", "idle")
            detail = data.get("phase_detail", "")
            icons = {
                "idle":     "💤 Warte auf nächstes Backup",
                "creating": f"⚙️ Backup wird erstellt… {detail}",
                "uploading":f"📤 Upload läuft… {detail}",
                "rotating": f"🗑️ Rotation läuft… {detail}",
                "success":  f"✅ Erfolgreich – {detail}",
                "error":    f"❌ Fehler – {detail}",
            }
            return icons.get(phase, f"❓ {phase}")

        btype_data = data.get(self.entity_description.backup_type, {})
        value = btype_data.get(self.entity_description.value_key)

        # Datum formatieren
        if self.entity_description.value_key == "last_date" and value:
            try:
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return dt.strftime("%d.%m.%Y %H:%M")
            except Exception:
                return value

        return value

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        if not data or not self.entity_description.backup_type:
            return {}
        btype_data = data.get(self.entity_description.backup_type, {})
        return {
            "letzter_name": btype_data.get("last_name"),
            "slug": btype_data.get("last_slug"),
        }
