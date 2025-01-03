sudo apt update
sudo apt -y install psmisc  python3-pip dnsmasq whois nmap curl arping dsniff frr iperf3 openvswitch-switch traceroute hping3 wireshark iperf
sudo git clone https://gitlab.com/exploit-database/exploitdb.git /opt/exploitdb
sudo ln -sf /opt/exploitdb/searchsploit /usr/local/bin/searchsploit
cp /opt/exploitdb/.searchsploit_rc ~/
export EDB_PATH="/opt/exploitdb"
searchsploit -u
sudo pip3 install pytest
