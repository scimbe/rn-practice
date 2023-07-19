#!/bin/bash

OUTPUT_FILE="installed_packages.txt"

# Erkennen und Speichern der mit apt installierten Pakete
apt list --installed | awk -F'/' '{print $1}' > "$OUTPUT_FILE"

echo "Die mit apt installierten Pakete wurden in $OUTPUT_FILE gesichert."
