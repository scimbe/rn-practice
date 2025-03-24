#!/bin/bash

# Strikte Fehlerbehandlung aktivieren
set -euo pipefail

# Lockfile zur Vermeidung paralleler Ausführung
LOCKFILE="/tmp/start_topology.lock"
if [[ -e "$LOCKFILE" ]]; then
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [ERROR] Lockfile $LOCKFILE gefunden. Ein anderer Prozess läuft?" >&2
    exit 1
fi
touch "$LOCKFILE"
trap 'rm -f "$LOCKFILE"' EXIT

# Logfunktion mit Fehlerebenen
log() {
    local level="INFO"
    if [[ $# -gt 1 ]]; then
        level="$1"
        shift
    fi
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [$level] $1" >&2
}

check_dependencies() {
    local missing_deps=()
    for cmd in python3 xterm zutty awk; do
        if ! command -v "$cmd" &>/dev/null && ! dpkg -l | grep -q "$cmd"; then
            missing_deps+=("$cmd")
        fi
    done
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log "ERROR" "Folgende Abhängigkeiten fehlen: ${missing_deps[*]}"
        log "INFO" "Bitte installieren Sie die fehlenden Pakete mit: sudo apt-get install ${missing_deps[*]}"
        exit 1
    fi
}

check_scripts() {
    local script_file="./getIntWithIntenet.sh"
    local topology_file="./topo03.py"
    if [[ ! -f "$script_file" ]]; then
        log "ERROR" "$script_file nicht gefunden."
        exit 1
    fi
    if [[ ! -x "$script_file" ]]; then
        log "WARNING" "$script_file ist nicht ausführbar. Setze Ausführungsrechte..."
        chmod +x "$script_file" || {
            log "ERROR" "Konnte Ausführungsrechte für $script_file nicht setzen."
            exit 1
        }
    fi
    if [[ ! -f "$topology_file" ]]; then
        log "ERROR" "$topology_file nicht gefunden."
        exit 1
    fi
}

cleanup() {
    log "INFO" "Aufräumen nach Fehler oder Unterbrechung..."
    sudo iptables -t nat -D POSTROUTING -o "$eth_interface" -j MASQUERADE &>/dev/null || log "WARNING" "Konnte NAT-Regel nicht entfernen."
    if [[ -f "$backup_resolv_conf" ]]; then
        log "INFO" "Stelle resolv.conf wieder her..."
        sudo mv "$backup_resolv_conf" "$resolv_conf" || log "WARNING" "Konnte Backup nicht wiederherstellen."
    fi
    sudo mn -c &>/dev/null || log "WARNING" "Mininet-Bereinigung fehlgeschlagen."
    for proc in zebra ripd bgpd xterm; do
        if pgrep "$proc" &>/dev/null; then
            sudo killall "$proc" &>/dev/null || log "WARNING" "Prozess $proc konnte nicht beendet werden."
        fi
    done
    sudo /etc/init.d/openvswitch-switch stop &>/dev/null || log "WARNING" "Open vSwitch konnte nicht gestoppt werden."
    log "INFO" "Aufräumen abgeschlossen."
    exit 1
}

trap cleanup SIGINT SIGTERM ERR

start_ovs() {
    log "INFO" "Open vSwitch wird gestartet"
    if ! sudo service openvswitch-switch status &>/dev/null; then
        sudo service openvswitch-switch start || {
            log "ERROR" "Open vSwitch konnte nicht gestartet werden."
            exit 1
        }
    else
        log "INFO" "Open vSwitch läuft bereits."
    fi
    sudo ovs-vsctl show &>/dev/null || {
        log "ERROR" "Open vSwitch scheint nicht korrekt zu funktionieren."
        exit 1
    }
}

configure_nat() {
    log "INFO" "Konfiguriere NAT für Internetzugriff"
    if ! ip link show eth0 &>/dev/null; then
        log "WARNING" "Interface eth0 nicht gefunden. Versuche Default-Interface zu bestimmen..."
        eth_interface=$(ip -4 route show default | awk '{print $5}' | head -n1)
        if [[ -z "$eth_interface" ]]; then
            log "ERROR" "Kein Default-Interface gefunden."
            return 1
        fi
    else
        eth_interface="eth0"
    fi
    if sudo iptables -t nat -C POSTROUTING -o "$eth_interface" -j MASQUERADE &>/dev/null; then
        log "INFO" "NAT-Regel existiert bereits."
    else
        sudo iptables -t nat -A POSTROUTING -o "$eth_interface" -j MASQUERADE || {
            log "ERROR" "NAT-Regel konnte nicht gesetzt werden."
            return 1
        }
    fi
    return 0
}

configure_nameserver() {
    resolv_conf="/etc/resolv.conf"
    backup_resolv_conf="/etc/resolv.conf.backup"
    nameserver="nameserver 10.0.1.2"

    if [[ ! -f "$resolv_conf" ]]; then
        log "ERROR" "$resolv_conf existiert nicht."
        exit 1
    fi

    log "INFO" "Backup von $resolv_conf wird erstellt"
    sudo cp "$resolv_conf" "$backup_resolv_conf" || {
        log "ERROR" "Backup fehlgeschlagen."
        exit 1
    }

    local temp_resolv
    temp_resolv=$(mktemp /tmp/resolv.conf.XXXXXX)

    awk -v ns="$nameserver" 'BEGIN {print ns} !seen[$0]++ && \$0 != ns {print}' "$backup_resolv_conf" > "$temp_resolv"
    if [[ ! -s "$temp_resolv" ]]; then
        log "ERROR" "Neue resolv.conf konnte nicht erstellt werden."
        sudo cp "$backup_resolv_conf" "$resolv_conf"
        exit 1
    fi

    sudo cp "$temp_resolv" "$resolv_conf" || {
        log "ERROR" "Neue resolv.conf konnte nicht angewendet werden."
        sudo cp "$backup_resolv_conf" "$resolv_conf"
        exit 1
    }

    sudo sed -i '/^nameserver .*:/d' "$resolv_conf"
    rm -f "$temp_resolv"
    log "INFO" "Nameserver wurde konfiguriert."
}

run_topology() {
    log "INFO" "Mininet wird bereinigt"
    mn -c || log "WARNING" "Mininet Cleanup fehlgeschlagen."
    log "INFO" "Topologie wird gestartet"
    sudo -E python3 topo03.py || {
        log "ERROR" "Topologie-Start fehlgeschlagen."
        return 1
    }
    return 0
}

restore_nameserver() {
    if [[ -f "$backup_resolv_conf" ]]; then
        sudo cp "$backup_resolv_conf" "$resolv_conf" || {
            log "ERROR" "Wiederherstellung der resolv.conf fehlgeschlagen."
            exit 1
        }
        sudo rm -f "$backup_resolv_conf"
    else
        log "WARNING" "Kein Backup für resolv.conf vorhanden."
    fi
}

main() {
    log "INFO" "Start der Topologie-Konfiguration"
    check_dependencies
    check_scripts
    start_ovs
    configure_nat || { log "ERROR" "NAT fehlgeschlagen."; cleanup; }
    ./getIntWithIntenet.sh || { log "ERROR" "getIntWithIntenet.sh fehlgeschlagen."; cleanup; }
    configure_nameserver
    run_topology || { log "ERROR" "Topologieausführung fehlgeschlagen."; restore_nameserver; cleanup; }
    mn -c || log "WARNING" "Mininet Cleanup fehlgeschlagen"
    for proc in xterm; do
        sudo killall "$proc" &>/dev/null || log "WARNING" "$proc nicht laufend."
    done
    restore_nameserver
    sudo service openvswitch-switch stop || log "WARNING" "OVS konnte nicht gestoppt werden."
    log "INFO" "Topologie-Konfiguration abgeschlossen."
    return 0
}

main "$@"

# Zusätzliches Cleanup (Redundant aber Absicherung)
for proc in xterm zebra ripd bgpd; do
    sudo killall "$proc" &>/dev/null || true
    done
