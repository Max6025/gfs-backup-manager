"""DataUpdateCoordinator mit WebSocket Push vom Addon."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, ADDON_API_PORT, ADDON_WS_PORT

_LOGGER = logging.getLogger(__name__)


class GFSBackupCoordinator(DataUpdateCoordinator):
    """Holt Daten vom GFS Backup Addon – primär via WebSocket Push."""

    def __init__(self, hass: HomeAssistant) -> None:
        # Fallback-Polling alle 60s falls WebSocket ausfällt
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=60),
        )
        self._api_url = f"http://127.0.0.1:{ADDON_API_PORT}"
        self._ws_url = f"ws://127.0.0.1:{ADDON_WS_PORT}"
        self._ws_task: asyncio.Task | None = None

    async def _async_setup(self) -> None:
        """WebSocket-Verbindung beim Start aufbauen."""
        await self._start_websocket()

    async def _start_websocket(self) -> None:
        """WebSocket-Listener starten."""
        if self._ws_task and not self._ws_task.done():
            return
        self._ws_task = self.hass.async_create_background_task(
            self._ws_listener(),
            "gfs_backup_ws_listener",
        )

    async def _ws_listener(self) -> None:
        """WebSocket-Verbindung zum Addon – reconnect bei Fehler."""
        import aiohttp
        _LOGGER.info("GFS WebSocket-Listener gestartet")
        while True:
            try:
                session = async_get_clientsession(self.hass)
                async with session.ws_connect(
                    self._ws_url,
                    heartbeat=30,
                    timeout=aiohttp.ClientTimeout(total=None, connect=10),
                ) as ws:
                    _LOGGER.info("GFS WebSocket verbunden")
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            try:
                                data = json.loads(msg.data)
                                if data.get("type") == "status_update":
                                    # Sofort Sensoren aktualisieren
                                    self.async_set_updated_data(
                                        self._enrich(data.get("data", {}))
                                    )
                            except Exception as e:
                                _LOGGER.debug("WS Parse-Fehler: %s", e)
                        elif msg.type in (
                            aiohttp.WSMsgType.CLOSED,
                            aiohttp.WSMsgType.ERROR,
                        ):
                            break
            except Exception as e:
                _LOGGER.debug("WS Verbindungsfehler: %s – reconnect in 10s", e)
            await asyncio.sleep(10)

    async def _async_update_data(self) -> dict:
        """Fallback HTTP-Polling."""
        try:
            session = async_get_clientsession(self.hass)
            async with session.get(
                f"{self._api_url}/status",
                timeout=10,
            ) as resp:
                if resp.status != 200:
                    raise UpdateFailed(f"HTTP {resp.status}")
                data = await resp.json()
                return self._enrich(data)
        except UpdateFailed:
            raise
        except Exception as err:
            raise UpdateFailed(f"Verbindung fehlgeschlagen: {err}") from err

    def _enrich(self, data: dict) -> dict:
        """Status mit berechneten Feldern anreichern."""
        config = data.get("config", {})
        for btype in ("daily", "weekly", "monthly", "yearly"):
            if btype in data:
                data[btype]["status"] = _calc_status(btype, data[btype])
                data[btype]["next_backup"] = _calc_next(btype, config)
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

    async def send_command(self, command: str) -> bool:
        """Befehl per HTTP ans Addon senden."""
        try:
            session = async_get_clientsession(self.hass)
            async with session.post(
                f"{self._api_url}/command",
                json={"command": command},
                timeout=10,
            ) as resp:
                return resp.status == 200
        except Exception as err:
            _LOGGER.error("Befehl '%s' Fehler: %s", command, err)
            return False

    async def async_config_entry_first_refresh(self) -> None:
        """Erst WebSocket starten, dann initialen Status holen."""
        await self._start_websocket()
        await super().async_config_entry_first_refresh()


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
            next_dt = now.replace(year=now.year+1,
                month=config.get("yearly_month", 1),
                day=config.get("yearly_day", 1),
                hour=int(h), minute=int(m), second=0, microsecond=0)
        else:
            return "Unbekannt"
        return next_dt.strftime("%d.%m.%Y %H:%M")
    except Exception:
        return "Unbekannt"
