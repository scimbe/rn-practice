#!/bin/bash

INPUT_FILE="installed_packages.txt"

# Überprüfen, ob die Eingabedatei vorhanden ist
if [ -f "$INPUT_FILE" ]; then
  # Wiederherstellen der gesicherten Pakete mit apt install
  sudo xargs apt install -y < "$INPUT_FILE"
  
  echo "Die gesicherten Pakete wurden wiederhergestellt."
else
  echo "Die Eingabedatei $INPUT_FILE existiert nicht."
  exit 1
fi
