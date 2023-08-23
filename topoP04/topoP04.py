from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import Controller
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel

class MyTopo(Topo):
    def build(self):
        # Erstellen von zwei Hosts
        h1 = self.addHost('h1', ip='10.0.0.1/24')
        h2 = self.addHost('h2', ip='10.0.0.2/24')

        # Erstellen eines Switches
        s1 = self.addSwitch('s1')

        # Verbinden der Hosts mit dem Switch mit begrenzter Bandbreite, kleiner MTU und Fehlerrate
        self.addLink(h1, s1, cls=TCLink, bw=10, mtu=536, loss=10) # 10% Fehlerrate
        self.addLink(h2, s1, cls=TCLink, bw=10, mtu=536, loss=10) # 10% Fehlerrate

if __name__ == '__main__':
    setLogLevel('info')
    topo = MyTopo()
    net = Mininet(topo=topo, controller=Controller)
    net.start()
    CLI(net)
    net.stop()

