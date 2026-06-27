"""Config Flow für GFS Backup Manager – Zero Config."""
from __future__ import annotations

import aiohttp
from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from .const import DOMAIN, ADDON_API_PORT


async def _check_addon_reachable(hass: HomeAssistant) -> bool:
    """Prüft ob der HTTP-Server im Addon erreichbar ist."""
    try:
        import aiohttp as aio
        async with aio.ClientSession() as session:
            async with session.get(
                f"http://127.0.0.1:{ADDON_API_PORT}/status",
                timeout=aio.ClientTimeout(total=5),
            ) as resp:
                return resp.status == 200
    except Exception:
        return False


class GFSBackupConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Zero-Config Flow – ein Klick, fertig."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Einziger Schritt."""
        # Nur eine Instanz erlauben
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        errors = {}

        if user_input is not None:
            reachable = await _check_addon_reachable(self.hass)
            if not reachable:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title="GFS Backup Manager",
                    data={},
                )

        # Beim ersten Aufruf ohne user_input direkt prüfen
        if user_input is None:
            reachable = await _check_addon_reachable(self.hass)
            if reachable:
                return self.async_create_entry(
                    title="GFS Backup Manager",
                    data={},
                )
            else:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            errors=errors,
            description_placeholders={
                "addon_url": f"http://127.0.0.1:{ADDON_API_PORT}"
            },
        )
