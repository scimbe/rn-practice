

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




echo "start topology"
start_ovs
#./getIntWithIntenet.sh
#sudo mv /etc/resolv.conf /etc/resolv.conf.old
#echo "nameserver 10.0.1.2" | sudo tee /etc/resolv.conf
#sudo bash -c  'echo "nameserver 1.1.1.1" >> /etc/resolv.conf'
sudo mn -c
sudo -E  python3 topoP03.py
sudo mn -c
sudo killall xterm
#sudo mv /etc/resolv.conf.old /etc/resolv.conf
