"""Config Flow für GFS Backup Manager – Zero Config."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from .const import DOMAIN, ADDON_SLUG


async def _check_addon_running(hass: HomeAssistant) -> bool:
    """Prüft ob das GFS Backup Addon läuft."""
    try:
        addon_info = await hass.components.hassio.async_get_addon_info(ADDON_SLUG)
        return addon_info.get("state") == "started"
    except Exception:
        return False


class GFSBackupConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Zero-Config Flow für GFS Backup Manager."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Einziger Schritt – prüft Addon und fertig."""
        # Nur eine Instanz erlauben
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None or True:
            # Addon prüfen
            addon_ok = await _check_addon_running(self.hass)
            if not addon_ok:
                return self.async_abort(reason="addon_not_found")

            return self.async_create_entry(
                title="GFS Backup Manager",
                data={"addon_slug": ADDON_SLUG},
            )

        return self.async_show_form(step_id="user")
