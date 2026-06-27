"""DataUpdateCoordinator für GFS Backup Manager."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, SCAN_INTERVAL_SECONDS, BACKUP_PREFIXES

_LOGGER = logging.getLogger(__name__)


class GFSBackupCoordinator(DataUpdateCoordinator):
    """Holt Backup-Daten vom HA Supervisor."""

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )

    async def _async_update_data(self) -> dict:
        """Backup-Liste vom Supervisor holen und auswerten."""
        try:
            session = async_get_clientsession(self.hass)

            # Korrekter Token-Zugriff in modernem HA
            from homeassistant.components.hassio import get_auth_token
            token = get_auth_token(self.hass)

            async with session.get(
                "http://supervisor/backups",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30,
            ) as resp:
                if resp.status != 200:
                    raise UpdateFailed(f"Supervisor API Fehler: {resp.status}")
                data = await resp.json()

            all_backups = data.get("data", {}).get("backups", [])

            # Addon-Status prüfen
            addon_running = await self._check_addon(token, session)

            result = {
                "addon_running": addon_running,
            }

            for btype, prefix in BACKUP_PREFIXES.items():
                typed = [
                    b for b in all_backups
                    if b.get("name", "").startswith(prefix)
                ]
                typed.sort(key=lambda x: x.get("date", ""), reverse=True)

                last = typed[0] if typed else None
                size_bytes = last.get("size", 0) if last else 0

                result[btype] = {
                    "count": len(typed),
                    "last_date": last.get("date") if last else None,
                    "last_name": last.get("name") if last else None,
                    "last_size_mb": round(size_bytes / 1024 / 1024, 1) if size_bytes else None,
                    "last_slug": last.get("slug") if last else None,
                    "status": _calc_status(btype, last),
                    "next_backup": _calc_next(btype),
                }

            return result

        except UpdateFailed:
            raise
        except Exception as err:
            raise UpdateFailed(f"Fehler: {err}") from err

    async def _check_addon(self, token: str, session) -> bool:
        """Prüft ob das Addon läuft."""
        try:
            from .const import ADDON_SLUG
            async with session.get(
                f"http://supervisor/addons/{ADDON_SLUG}/info",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            ) as resp:
                if resp.status == 200:
                    info = await resp.json()
                    return info.get("data", {}).get("state") == "started"
        except Exception:
            pass
        return False


def _calc_status(btype: str, last: dict | None) -> str:
    """Status basierend auf Alter des letzten Backups."""
    if last is None:
        return "Kein Backup"

    try:
        last_date_str = last.get("date", "")
        last_date = datetime.fromisoformat(last_date_str.replace("Z", "+00:00"))
        now = datetime.now(last_date.tzinfo)
        age = now - last_date

        thresholds = {
            "daily": timedelta(days=2),
            "weekly": timedelta(weeks=2),
            "monthly": timedelta(days=45),
            "yearly": timedelta(days=400),
        }

        if age > thresholds.get(btype, timedelta(days=2)):
            return "Überfällig"
        return "OK"
    except Exception:
        return "Unbekannt"


def _calc_next(btype: str) -> str:
    """Nächstes geplantes Backup (Schätzung)."""
    now = datetime.now()
    try:
        if btype == "daily":
            next_dt = (now + timedelta(days=1)).replace(
                hour=3, minute=0, second=0, microsecond=0)
        elif btype == "weekly":
            days = (6 - now.weekday()) % 7 or 7
            next_dt = (now + timedelta(days=days)).replace(
                hour=4, minute=0, second=0, microsecond=0)
        elif btype == "monthly":
            if now.month == 12:
                next_dt = now.replace(
                    year=now.year + 1, month=1, day=1,
                    hour=5, minute=0, second=0, microsecond=0)
            else:
                next_dt = now.replace(
                    month=now.month + 1, day=1,
                    hour=5, minute=0, second=0, microsecond=0)
        elif btype == "yearly":
            next_dt = now.replace(
                year=now.year + 1, month=1, day=1,
                hour=6, minute=0, second=0, microsecond=0)
        else:
            return "Unbekannt"
        return next_dt.strftime("%d.%m.%Y %H:%M")
    except Exception:
        return "Unbekannt"
