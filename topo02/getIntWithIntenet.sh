#!/bin/bash

OUTPUT_FILE="interface.txt"

# Funktion zum Überprüfen der Internetverbindung
check_internet_connection() {
  ping -c 1 google.com >/dev/null 2>&1
  if [ $? -eq 0 ]; then
    echo "Internetverbindung ist vorhanden"
  else
    echo "Keine Internetverbindung"
  fi
}

# Funktion zum Ermitteln des Netzwerkinterfaces mit Internetverbindung
get_interface_with_internet() {
  interfaces=$(ip -o link show | awk -F': ' '{print $2}')

  for interface in $interfaces; do
    if [ "$interface" != "lo" ]; then
      check_internet_connection
      if [ $? -eq 0 ]; then
        gateway=$(ip -o -4 route show default | awk '{print $3}')
        echo "$interface" > "$OUTPUT_FILE"
        echo "Gateway-IP-Adresse: $gateway"
        echo "$gateway" >> "$OUTPUT_FILE"
        echo "Netzwerkinterface mit Internetverbindung: $interface"
        exit 0
      fi
    fi
  done

  echo "Kein Netzwerkinterface mit Internetverbindung gefunden"
  exit 1
}

get_interface_with_internet

