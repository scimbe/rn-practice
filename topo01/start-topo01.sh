#!/bin/bash

# Strikte Fehlerbehandlung aktivieren
set -euo pipefail

# Logfunktion mit Fehlerebenen
log() {
    local level="INFO"
    if [[ $# -gt 1 ]]; then
        level="$1"
        shift
    fi
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [$level] $1" >&2
}

# Prüfung auf Root-Rechte
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log "ERROR" "Dieses Skript benötigt Root-Rechte. Bitte mit sudo ausführen."
        exit 1
    fi
}

# Prüfung auf vorhandene Software
check_dependencies() {
    local missing_deps=()
    
    # Überprüfung der erforderlichen Pakete
    for cmd in python3 xterm zutty awk; do
        if ! command -v "$cmd" &> /dev/null && ! dpkg -l | grep -q "$cmd"; then
            missing_deps+=("$cmd")
        fi
    done
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log "ERROR" "Folgende Abhängigkeiten fehlen: ${missing_deps[*]}"
        log "INFO" "Bitte installieren Sie die fehlenden Pakete mit: sudo apt-get install ${missing_deps[*]}"
        exit 1
    fi
}

# Prüfung auf Skriptdateien mit Fehlerbehandlung
check_scripts() {
    local script_file="./getIntWithIntenet.sh"
    local topology_file="./topo01.py"
    
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

# Aufräumfunktion für fehlerhafte Beendigung
cleanup() {
    log "INFO" "Aufräumen nach Fehler oder Unterbrechung..."

    # NAT-Regel entfernen
    log "INFO" "Entferne NAT-Regel..."
    iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE &>/dev/null || log "WARNING" "Konnte NAT-Regel nicht entfernen."
    
    
    # Prüfe, ob Backup-Datei existiert und stelle sie wieder her
    if [[ -f "$backup_resolv_conf" ]]; then
        log "INFO" "Stelle resolv.conf wieder her..."
        mv "$backup_resolv_conf" "$resolv_conf" || log "WARNING" "Konnte Backup nicht wiederherstellen."
    fi
    
    # Beende laufende mininet-Instanzen
    log "INFO" "Bereinige Mininet..."
    mn -c &>/dev/null || log "WARNING" "Mininet-Bereinigung fehlgeschlagen."
    
    # Beende alle xterm-Prozesse
    log "INFO" "Beende xterm-Prozesse..."
    killall xterm &>/dev/null || log "WARNING" "Keine laufenden xterm-Prozesse gefunden."
    
    # Stelle sicher, dass Open vSwitch gestoppt wird
    log "INFO" "Stoppe Open vSwitch..."
    /etc/init.d/openvswitch-switch stop &>/dev/null || log "WARNING" "Open vSwitch konnte nicht gestoppt werden."
    
    log "INFO" "Aufräumen abgeschlossen."
    exit 1
}

# Trap für sauberes Aufräumen bei Abbruch
trap cleanup SIGINT SIGTERM ERR

# Hauptfunktionen
start_ovs() {
    log "INFO" "Open vSwitch wird gestartet"
    if ! service openvswitch-switch status &>/dev/null; then
        service openvswitch-switch start || {
            log "ERROR" "Open vSwitch konnte nicht gestartet werden. Ist das Paket installiert?"
            exit 1
        }
    else
        log "INFO" "Open vSwitch läuft bereits."
    fi
    
    # Überprüfe, ob OVS tatsächlich läuft
    ovs-vsctl show &>/dev/null || {
        log "ERROR" "Open vSwitch scheint nicht korrekt zu funktionieren."
        exit 1
    }
}

configure_nat() {
    log "INFO" "Konfiguriere NAT für Internetzugriff"
    
    # Prüfe, ob das eth0-Interface existiert
    if ! ip link show eth0 &>/dev/null; then
        log "WARNING" "Interface eth0 nicht gefunden. Versuche, das Standard-Interface zu bestimmen..."
        local default_iface=$(ip -4 route show default | awk '{print $5}' | head -n1)
        
        if [[ -z "$default_iface" ]]; then
            log "ERROR" "Kein Default-Interface gefunden. NAT kann nicht konfiguriert werden."
            return 1
        fi
        
        log "INFO" "Verwende $default_iface anstelle von eth0"
        eth_interface="$default_iface"
    else
        eth_interface="eth0"
    fi
    
    # Prüfe, ob die NAT-Regel bereits existiert
    if iptables -t nat -C POSTROUTING -o "$eth_interface" -j MASQUERADE &>/dev/null; then
        log "INFO" "NAT-Regel existiert bereits."
    else
        log "INFO" "Füge NAT-Regel hinzu: POSTROUTING -o $eth_interface -j MASQUERADE"
        iptables -t nat -A POSTROUTING -o "$eth_interface" -j MASQUERADE || {
            log "ERROR" "Konnte NAT-Regel nicht einrichten. Prüfen Sie die Rechte und iptables-Konfiguration."
            return 1
        }
    fi

    return 0
}
 
configure_nameserver() {
    resolv_conf="/etc/resolv.conf"
    backup_resolv_conf="/etc/resolv.conf.backup"
    nameserver="nameserver 10.0.1.2"
    
    # Prüfe, ob resolv.conf existiert und lesbar ist
    if [[ ! -f "$resolv_conf" ]]; then
        log "ERROR" "$resolv_conf existiert nicht."
        exit 1
    fi
    
    log "INFO" "Backup der aktuellen $resolv_conf wird erstellt"
    if ! cp "$resolv_conf" "$backup_resolv_conf"; then
        log "ERROR" "Backup von $resolv_conf fehlgeschlagen. Prüfen Sie die Rechte."
        exit 1
    fi
    
    log "INFO" "Prüfen, ob Nameserver $nameserver bereits in $resolv_conf existiert"
    
    # Nameserver einfügen, wenn nicht vorhanden oder an den Anfang verschieben
    awk -v ns="$nameserver" '
    BEGIN {print ns}
    !seen[$0]++ && $0 != ns {print}
    ' "$backup_resolv_conf" > "/tmp/resolv.conf.new"
    
    # Prüfe, ob die neue Datei erstellt wurde
    if [[ ! -s "/tmp/resolv.conf.new" ]]; then
        log "ERROR" "Konnte neue resolv.conf nicht erstellen."
        cp "$backup_resolv_conf" "$resolv_conf"
        exit 1
    fi
    
    # Ersetzung nur durchführen, wenn die Datei erfolgreich erstellt wurde
    cp "/tmp/resolv.conf.new" "$resolv_conf" || {
        log "ERROR" "Konnte neue resolv.conf nicht anwenden."
        cp "$backup_resolv_conf" "$resolv_conf"
        exit 1
    }
    rm -f "/tmp/resolv.conf.new"
    
    log "INFO" "Nameserver wurde an den Anfang der Liste gesetzt."
}

run_topology() {
    log "INFO" "Mininet wird bereinigt"
    mn -c || log "WARNING" "Mininet Cleanup fehlgeschlagen, fahre trotzdem fort."
    
    log "INFO" "Topologie wird gestartet"
    if ! python3 topo01.py; then
        log "ERROR" "Topologie-Start fehlgeschlagen."
        return 1
    fi
    
    return 0
}

restore_nameserver() {
    log "INFO" "Backup der resolv.conf wird zurückgespielt"
    if [[ -f "$backup_resolv_conf" ]]; then
        if ! cp "$backup_resolv_conf" "$resolv_conf"; then
            log "ERROR" "Wiederherstellung der resolv.conf fehlgeschlagen."
            exit 1
        fi
        rm -f "$backup_resolv_conf"
    else
        log "WARNING" "Backup-Datei für resolv.conf nicht gefunden."
    fi
}

# Hauptprogramm
main() {
    log "INFO" "Start der Topologie-Konfiguration"
    
    check_root
    check_dependencies
    check_scripts
    
    start_ovs

    # Konfiguriere NAT für Internetzugriff
    if ! configure_nat; then
        log "ERROR" "NAT-Konfiguration fehlgeschlagen."
        cleanup
    fi
    
    # Führe getIntWithIntenet.sh aus mit Fehlerbehandlung
    if ! ./getIntWithIntenet.sh; then
        log "ERROR" "getIntWithIntenet.sh fehlgeschlagen."
        cleanup
    fi
    
    configure_nameserver
    
    if ! run_topology; then
        log "ERROR" "Topologie konnte nicht ausgeführt werden."
        restore_nameserver
        cleanup
    fi
    
    log "INFO" "Mininet wird erneut bereinigt"
    mn -c || log "WARNING" "Mininet Cleanup fehlgeschlagen"
    
    log "INFO" "xterm-Prozesse werden beendet"
    killall xterm 2>/dev/null || log "WARNING" "Keine laufenden xterm-Prozesse gefunden"
    
    restore_nameserver
    
    log "INFO" "Open vSwitch wird gestoppt"
    service openvswitch-switch stop || log "WARNING" "Open vSwitch konnte nicht gestoppt werden"
    
    log "INFO" "Topologie-Konfiguration erfolgreich abgeschlossen"
    return 0
}

# Starte das Hauptprogramm
main "$@"
