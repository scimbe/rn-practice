echo "start topology"
./getIntWithIntenet.sh

resolv_conf="/etc/resolv.conf"
sudo cp $resolv_conf /etc/resolv.conf.old

# Nameserver, der hinzugefügt werden soll, falls nicht vorhanden
nameserver="nameserver 10.0.1.2"

# Überprüfen, ob der Nameserver bereits in der Datei vorhanden ist
if ! grep -q "^$nameserver$" "$resolv_conf"; then
    echo "Der Nameserver $nameserver wird hinzugefügt."
    # Hinzufügen des Nameservers am Ende der Datei
    echo "$nameserver" | sudo tee -a "$resolv_conf" > /dev/null
else
    echo "Der Nameserver $nameserver ist bereits in der Datei vorhanden."
fi

sudo mn -c
sudo -E  python3 topo01.py
sudo mn -c
sudo killall xterm
sudo mv /etc/resolv.conf.old /etc/resolv.conf
