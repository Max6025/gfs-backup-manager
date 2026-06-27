# GFS Backup Manager – Home Assistant Integration

HACS Integration für das [GFS Backup Addon](https://github.com/Max6025/gfs-backup-addon).

## Features

- 📊 **Sensoren** pro Backup-Ebene (täglich/wöchentlich/monatlich/jährlich):
  - Status (OK / Überfällig / Kein Backup vorhanden)
  - Datum des letzten Backups
  - Nächstes geplantes Backup
  - Anzahl der Backups
  - Größe des letzten Backups (MB)

- 🔘 **Buttons**:
  - Backup sofort starten (pro Ebene)
  - Letztes Backup löschen (lokal & NAS, pro Ebene)

- ⚡ **Zero Config** – verbindet sich automatisch mit dem Addon

## Voraussetzung

Das [GFS Backup Addon](https://github.com/Max6025/gfs-backup-addon) muss installiert und gestartet sein.

## Installation via HACS

1. HACS → Integrationen → ⋮ → Benutzerdefinierte Repositories
2. URL: `https://github.com/Max6025/gfs-backup-manager`
3. Kategorie: Integration
4. Hinzufügen → "GFS Backup Manager" suchen → Installieren
5. HA neu starten
6. Einstellungen → Integrationen → Integration hinzufügen → "GFS Backup Manager"
