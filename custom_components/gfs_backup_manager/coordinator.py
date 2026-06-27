"""DataUpdateCoordinator – fragt HTTP-Server im Addon ab."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, SCAN_INTERVAL_SECONDS, ADDON_API_PORT

_LOGGER = logging.getLogger(__name__)


def _get_addon_url(hass: HomeAssistant) -> str:
    """HA-Host IP ermitteln und Addon-URL zusammenbauen."""
    # In HA läuft alles auf localhost – der Port ist nach außen freigegeben
    return f"http://127.0.0.1:{ADDON_API_PORT}"


class GFSBackupCoordinator(DataUpdateCoordinator):
    """Holt Daten vom GFS Backup Addon HTTP-Server."""

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self._api_url = _get_addon_url(hass)

    async def _async_update_data(self) -> dict:
        try:
            session = async_get_clientsession(self.hass)
            async with session.get(
                f"{self._api_url}/status",
                timeout=10,
            ) as resp:
                if resp.status != 200:
                    raise UpdateFailed(f"Addon HTTP-Server Fehler: {resp.status}")
                data = await resp.json()

            for btype in ("daily", "weekly", "monthly", "yearly"):
                if btype in data:
                    data[btype]["status"] = _calc_status(btype, data[btype])
                    data[btype]["next_backup"] = _calc_next(btype, data.get("config", {}))
                    size = data[btype].get("last_size", 0)
                    data[btype]["last_size_mb"] = round(size / 1024 / 1024, 1) if size else None
                    raw_date = data[btype].get("last_date")
                    if raw_date:
                        try:
                            dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                            data[btype]["last_date_fmt"] = dt.strftime("%d.%m.%Y %H:%M")
                        except Exception:
                            data[btype]["last_date_fmt"] = raw_date
                    else:
                        data[btype]["last_date_fmt"] = None

            return data

        except UpdateFailed:
            raise
        except Exception as err:
            raise UpdateFailed(f"Verbindung zum Addon fehlgeschlagen: {err}") from err

    async def send_command(self, command: str) -> bool:
        """Befehl direkt per HTTP an Addon senden."""
        try:
            session = async_get_clientsession(self.hass)
            async with session.post(
                f"{self._api_url}/command",
                json={"command": command},
                timeout=10,
            ) as resp:
                ok = resp.status == 200
                if ok:
                    _LOGGER.info("Befehl '%s' erfolgreich gesendet", command)
                else:
                    _LOGGER.error("Befehl '%s' fehlgeschlagen: HTTP %s", command, resp.status)
                return ok
        except Exception as err:
            _LOGGER.error("Befehl '%s' Fehler: %s", command, err)
            return False


def _calc_status(btype: str, data: dict) -> str:
    last_date = data.get("last_date")
    if not last_date:
        return "Kein Backup"
    try:
        dt = datetime.fromisoformat(last_date.replace("Z", "+00:00"))
        age = datetime.now(dt.tzinfo) - dt
        thresholds = {
            "daily": timedelta(days=2),
            "weekly": timedelta(weeks=2),
            "monthly": timedelta(days=45),
            "yearly": timedelta(days=400),
        }
        return "Überfällig" if age > thresholds.get(btype, timedelta(days=2)) else "OK"
    except Exception:
        return "Unbekannt"


def _calc_next(btype: str, config: dict) -> str:
    now = datetime.now()
    try:
        if btype == "daily":
            h, m = config.get("daily_time", "03:00").split(":")
            next_dt = (now + timedelta(days=1)).replace(
                hour=int(h), minute=int(m), second=0, microsecond=0)
        elif btype == "weekly":
            h, m = config.get("weekly_time", "04:00").split(":")
            days = (6 - now.weekday()) % 7 or 7
            next_dt = (now + timedelta(days=days)).replace(
                hour=int(h), minute=int(m), second=0, microsecond=0)
        elif btype == "monthly":
            h, m = config.get("monthly_time", "05:00").split(":")
            day = config.get("monthly_day", 1)
            if now.month == 12:
                next_dt = now.replace(year=now.year+1, month=1, day=day,
                    hour=int(h), minute=int(m), second=0, microsecond=0)
            else:
                next_dt = now.replace(month=now.month+1, day=day,
                    hour=int(h), minute=int(m), second=0, microsecond=0)
        elif btype == "yearly":
            h, m = config.get("yearly_time", "06:00").split(":")
            day = config.get("yearly_day", 1)
            month = config.get("yearly_month", 1)
            next_dt = now.replace(year=now.year+1, month=month, day=day,
                hour=int(h), minute=int(m), second=0, microsecond=0)
        else:
            return "Unbekannt"
        return next_dt.strftime("%d.%m.%Y %H:%M")
    except Exception:
        return "Unbekannt"
