#!/bin/bash

set -euo pipefail  # Aktiviert strikte Fehlerbehandlung

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

log "Start der Topologie-Konfiguration"

log "Open vSwitch wird gestartet"
sudo /etc/init.d/openvswitch-switch start || log "Warnung: Open vSwitch konnte nicht gestartet werden"

# Sicherstellen, dass das erforderliche Skript vorhanden ist
if [[ ! -x ./getIntWithIntenet.sh ]]; then
    log "Fehler: ./getIntWithIntenet.sh nicht gefunden oder nicht ausführbar."
    exit 1
fi

./getIntWithIntenet.sh

resolv_conf="/etc/resolv.conf"
backup_resolv_conf="/etc/resolv.conf.old"
nameserver="nameserver 10.0.1.2"

log "Backup der aktuellen $resolv_conf wird erstellt"

if ! sudo cp "$resolv_conf" "$backup_resolv_conf"; then
    log "Fehler: Backup von $resolv_conf fehlgeschlagen."
    exit 1
fi

log "Prüfen, ob Nameserver $nameserver bereits in $resolv_conf existiert"

if ! grep -qxF "$nameserver" "$resolv_conf"; then
    log "Nameserver wird hinzugefügt."
    echo "$nameserver" | sudo tee -a "$resolv_conf" > /dev/null
else
    log "Nameserver ist bereits vorhanden. Keine Aktion erforderlich."
fi

log "Mininet wird bereinigt"
sudo mn -c || log "Warnung: Mininet Cleanup fehlgeschlagen"

log "Topologie wird gestartet"
if ! sudo -E python3 topo01.py; then
    log "Fehler: Topologie-Start fehlgeschlagen."
    sudo mv "$backup_resolv_conf" "$resolv_conf"
    exit 1
fi

log "Mininet wird erneut bereinigt"
sudo mn -c || log "Warnung: Mininet Cleanup fehlgeschlagen"

log "xterm-Prozesse werden beendet"
sudo killall xterm || log "Warnung: Keine laufenden xterm-Prozesse gefunden"

log "Backup der resolv.conf wird zurückgespielt"
if ! sudo mv "$backup_resolv_conf" "$resolv_conf"; then
    log "Fehler: Wiederherstellung der resolv.conf fehlgeschlagen."
    exit 1
fi

log "Open vSwitch wird gestoppt"
sudo /etc/init.d/openvswitch-switch stop || log "Warnung: Open vSwitch konnte nicht gestoppt werden"

log "Topologie-Konfiguration abgeschlossen"
