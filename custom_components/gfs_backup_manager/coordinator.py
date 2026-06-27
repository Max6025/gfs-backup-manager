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
        self.hass = hass

    async def _async_update_data(self) -> dict:
        """Backup-Liste vom Supervisor holen und auswerten."""
        try:
            session = async_get_clientsession(self.hass)
            token = self.hass.components.hassio.get_auth_token()

            async with session.get(
                "http://supervisor/backups",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30,
            ) as resp:
                if resp.status != 200:
                    raise UpdateFailed(f"Supervisor API Fehler: {resp.status}")
                data = await resp.json()

            all_backups = data.get("data", {}).get("backups", [])

            result = {}
            for btype, prefix in BACKUP_PREFIXES.items():
                # Nur GFS-Backups dieses Typs
                typed = [
                    b for b in all_backups
                    if b.get("name", "").startswith(prefix)
                ]
                typed.sort(key=lambda x: x.get("date", ""), reverse=True)

                last = typed[0] if typed else None
                result[btype] = {
                    "last_backup": last,
                    "count": len(typed),
                    "last_date": last.get("date") if last else None,
                    "last_name": last.get("name") if last else None,
                    "last_size": last.get("size") if last else None,
                    "last_slug": last.get("slug") if last else None,
                    "status": _calc_status(btype, last),
                    "next_backup": _calc_next(btype),
                }

            return result

        except Exception as err:
            raise UpdateFailed(f"Fehler beim Abrufen der Backup-Daten: {err}") from err


def _calc_status(btype: str, last: dict | None) -> str:
    """Berechnet den Status basierend auf dem letzten Backup-Datum."""
    if last is None:
        return "Kein Backup vorhanden"

    try:
        last_date_str = last.get("date", "")
        # ISO Format: 2026-06-27T15:30:00+00:00
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
    """Berechnet wann das nächste Backup fällig ist (grobe Schätzung)."""
    now = datetime.now()
    if btype == "daily":
        next_dt = (now + timedelta(days=1)).replace(hour=3, minute=0, second=0)
    elif btype == "weekly":
        days_until_sunday = (6 - now.weekday()) % 7 or 7
        next_dt = (now + timedelta(days=days_until_sunday)).replace(hour=4, minute=0, second=0)
    elif btype == "monthly":
        if now.month == 12:
            next_dt = now.replace(year=now.year + 1, month=1, day=1, hour=5, minute=0, second=0)
        else:
            next_dt = now.replace(month=now.month + 1, day=1, hour=5, minute=0, second=0)
    elif btype == "yearly":
        next_dt = now.replace(year=now.year + 1, month=1, day=1, hour=6, minute=0, second=0)
    else:
        return "Unbekannt"

    return next_dt.strftime("%d.%m.%Y %H:%M")
