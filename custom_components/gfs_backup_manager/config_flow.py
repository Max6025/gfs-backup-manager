"""Config Flow für GFS Backup Manager – Zero Config."""
from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.components.hassio import is_hassio, get_supervisor_ip

from .const import DOMAIN, ADDON_SLUG


async def _check_addon_running(hass: HomeAssistant) -> bool:
    """Prüft ob das GFS Backup Addon läuft."""
    try:
        from homeassistant.components.hassio import async_get_addon_info
        info = await async_get_addon_info(hass, ADDON_SLUG)
        return info.get("state") == "started"
    except Exception:
        return False


class GFSBackupConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Zero-Config Flow – ein Klick, fertig."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Direkt einrichten ohne Formular."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        addon_ok = await _check_addon_running(self.hass)
        if not addon_ok:
            return self.async_abort(reason="addon_not_found")

        return self.async_create_entry(
            title="GFS Backup Manager",
            data={"addon_slug": ADDON_SLUG},
        )
