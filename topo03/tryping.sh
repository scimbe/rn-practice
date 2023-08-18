#!/bin/bash

# Ersetzen Sie "example.com" durch die Adresse des gewünschten Hosts
host=$1
# Versuche solange einen Ping, bis es eine Verbindung zum Host hat
while ! ping -c 1 "$host" &> /dev/null; do
    echo "Ping zu $host fehlgeschlagen. Versuche es erneut..."
    sleep 1
done

# Führe den Ping 10 Mal durch, nachdem eine Verbindung hergestellt ist
echo "Verbindung zu $host hergestellt. Führe Ping 10 Mal durch..."
ping -c 10 "$host"
