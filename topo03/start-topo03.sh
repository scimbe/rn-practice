echo "start topology"
#./getIntWithIntenet.sh
#sudo mv /etc/resolv.conf /etc/resolv.conf.old
#echo "nameserver 10.0.1.2" | sudo tee /etc/resolv.conf
#sudo bash -c  'echo "nameserver 1.1.1.1" >> /etc/resolv.conf'
sudo mn -c
sudo -E  python3 topo03.py
sudo mn -c
sudo killall xterm
#sudo mv /etc/resolv.conf.old /etc/resolv.conf
