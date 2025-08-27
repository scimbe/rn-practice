from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import Controller, RemoteController, Node
from mininet.cli import CLI
from mininet.log import setLogLevel

class MyTopo(Topo):
    def build(self):
        # Erstellen von zwei Switches
        
        s1 = self.addSwitch('s1', failMode='standalone')
        s2 = self.addSwitch('s2', failMode='standalone')


        # Erstellen von zwei Hosts für Netzwerk 1 ohne IP-Adressen
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')

        # Erstellen von zwei Hosts für Netzwerk 2 ohne IP-Adressen
        h3 = self.addHost('h3')
        h4 = self.addHost('h4')

        # Erstellen eines Routers
        r1 = self.addNode('r1')
        self.addLink(r1, s1)
        self.addLink(r1, s2)

        # Verbinden der Hosts mit den Switches
        self.addLink(h1, s1)
        self.addLink(h2, s1)
        self.addLink(h3, s2)
        self.addLink(h4, s2)

def configureRouter(net):
    router = net.get('r1')
    router.cmd('echo 1 > /proc/sys/net/ipv4/ip_forward')

if __name__ == '__main__':
    setLogLevel('info')
    topo = MyTopo()
    net = Mininet(topo=topo, controller=lambda name: RemoteController(name, ip='127.0.0.1'))
    net.start()
    configureRouter(net)
    CLI(net)
    net.stop()

