#!/bin/bash

# Systempakete aktualisieren
sudo apt update

# Notwendige Pakete installieren
sudo apt -y install psmisc python3-pip dnsmasq whois nmap curl arping dsniff frr iperf3 openvswitch-switch traceroute hping3 wireshark iperf

# Überprüfen, ob das Verzeichnis /opt/exploitdb bereits existiert
if [ -d "/opt/exploitdb" ]; then
    echo "Das Verzeichnis /opt/exploitdb existiert bereits. Überspringe das Klonen des Repositories."
else
    # Exploit Database Repository klonen
    sudo git clone https://gitlab.com/exploit-database/exploitdb.git /opt/exploitdb
fi

# Überprüfen, ob der symbolische Link bereits existiert und korrekt ist
if [ -L "/usr/local/bin/searchsploit" ] && [ "$(readlink -f /usr/local/bin/searchsploit)" == "/opt/exploitdb/searchsploit" ]; then
    echo "Der symbolische Link /usr/local/bin/searchsploit existiert bereits und zeigt auf /opt/exploitdb/searchsploit."
else
    # Symbolischen Link für SearchSploit erstellen
    sudo ln -sf /opt/exploitdb/searchsploit /usr/local/bin/searchsploit
fi

# Konfigurationsdatei für SearchSploit ins Home-Verzeichnis kopieren, falls sie nicht existiert
if [ -f "$HOME/.searchsploit_rc" ]; then
    echo "Die Datei .searchsploit_rc existiert bereits im Home-Verzeichnis. Überspringe das Kopieren."
else
    cp /opt/exploitdb/.searchsploit_rc ~/
fi

# Überprüfen, ob die export-Anweisung bereits in .bashrc vorhanden ist
if grep -Fxq 'export EDB_PATH="/opt/exploitdb"' ~/.bashrc; then
    echo "Die Umgebungsvariable EDB_PATH ist bereits in .bashrc gesetzt."
else
    # export-Anweisung zu .bashrc hinzufügen
    echo 'export EDB_PATH="/opt/exploitdb"' >> ~/.bashrc
    echo "Die Umgebungsvariable EDB_PATH wurde zu .bashrc hinzugefügt."
fi

# Aktuelle Shell-Umgebung aktualisieren
export EDB_PATH="/opt/exploitdb"

# SearchSploit Datenbank aktualisieren
searchsploit -u

# pytest mit pip3 installieren
sudo pip3 install pytest
