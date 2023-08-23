from mininet.topo import Topo
from mininet.net import Mininet
from mininet.link import TCLink, Link
from mininet.node import Node
from mininet.log import setLogLevel, info
from mininet.cli import CLI

class Router( Node ):
    "Node, der als Router innerhalb von Mininet fungiert."

    def config( self, **params ):
        super( Router, self).config( **params )
        self.cmd( 'sysctl net.ipv4.ip_forward=1' )

    def terminate( self ):
        self.cmd( 'sysctl net.ipv4.ip_forward=0' )
        super( Router, self ).terminate()

class NetworkTopology( Topo ):
    def build( self, **_opts ):
        r1, r2, r3 = [ self.addHost( 'r%s' % i, cls=Router )
                       for i in (1, 2, 3) ]
        

        h1=self.addHost('h1')
        h2=self.addHost('h2')
        h3=self.addHost('h3')
        h4=self.addHost('h4')
        
        self.addLink( r1, h1, intfName1='r1-eth0', intfName2='h1-eth0' )
        self.addLink( r2, h2, intfName1='r2-eth0', intfName2='h2-eth0' )
        self.addLink( r1, r2, intfName1='r1-eth1', intfName2='r2-eth1')
        self.addLink( r2, r3, intfName1='r2-eth2', intfName2='r3-eth0' )
        self.addLink( r3, h3, intfName1='r3-eth1',  intfName2='h3-eth0' )
        self.addLink( r3, h4, intfName1='r3-eth2',  intfName2='h3-eth0' )
 


def run():
    "Testfunktion für das Netzwerk"
    topo = NetworkTopology()
    net = Mininet( topo=topo,link=TCLink  )
    net.start()
   

    info( 'Das Netzwerk ist nun einsatzbereit.\n' )
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel( 'info' )
    run()

