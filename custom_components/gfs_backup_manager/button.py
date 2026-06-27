"""Buttons für GFS Backup Manager."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ADDON_SLUG
from .coordinator import GFSBackupCoordinator

_LOGGER = logging.getLogger(__name__)

DEVICE_INFO = DeviceInfo(
    identifiers={(DOMAIN, "gfs_backup_manager")},
    name="GFS Backup Manager",
    manufacturer="Max6025",
    model="GFS Backup Addon",
)


@dataclass
class GFSButtonDescription(ButtonEntityDescription):
    command: str = ""


BUTTON_TYPES: list[GFSButtonDescription] = [
    GFSButtonDescription(
        key="trigger_daily",
        name="GFS Tägliches Backup jetzt starten",
        icon="mdi:backup-restore",
        command="trigger_daily",
    ),
    GFSButtonDescription(
        key="trigger_weekly",
        name="GFS Wöchentliches Backup jetzt starten",
        icon="mdi:backup-restore",
        command="trigger_weekly",
    ),
    GFSButtonDescription(
        key="trigger_monthly",
        name="GFS Monatliches Backup jetzt starten",
        icon="mdi:backup-restore",
        command="trigger_monthly",
    ),
    GFSButtonDescription(
        key="trigger_yearly",
        name="GFS Jährliches Backup jetzt starten",
        icon="mdi:backup-restore",
        command="trigger_yearly",
    ),
    GFSButtonDescription(
        key="delete_last_local",
        name="GFS Letztes lokales Backup löschen",
        icon="mdi:delete-clock",
        command="delete_last_local",
    ),
    GFSButtonDescription(
        key="delete_last_nas_daily",
        name="GFS Letztes NAS-Backup löschen (täglich)",
        icon="mdi:delete-clock",
        command="delete_last_nas_daily",
    ),
    GFSButtonDescription(
        key="delete_last_nas_weekly",
        name="GFS Letztes NAS-Backup löschen (wöchentlich)",
        icon="mdi:delete-clock",
        command="delete_last_nas_weekly",
    ),
    GFSButtonDescription(
        key="delete_last_nas_monthly",
        name="GFS Letztes NAS-Backup löschen (monatlich)",
        icon="mdi:delete-clock",
        command="delete_last_nas_monthly",
    ),
    GFSButtonDescription(
        key="delete_last_nas_yearly",
        name="GFS Letztes NAS-Backup löschen (jährlich)",
        icon="mdi:delete-clock",
        command="delete_last_nas_yearly",
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: GFSBackupCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        GFSBackupButton(coordinator, description)
        for description in BUTTON_TYPES
    )


class GFSBackupButton(CoordinatorEntity, ButtonEntity):
    """GFS Backup Button."""

    entity_description: GFSButtonDescription

    def __init__(self, coordinator: GFSBackupCoordinator, description: GFSButtonDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"gfs_backup_{description.key}"
        self._attr_device_info = DEVICE_INFO

    async def async_press(self) -> None:
        """Befehl per HTTP direkt ans Addon senden."""
        _LOGGER.info("GFS Button: %s", self.entity_description.command)
        ok = await self.coordinator.send_command(self.entity_description.command)
        if ok:
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Button %s fehlgeschlagen", self.entity_description.command)
