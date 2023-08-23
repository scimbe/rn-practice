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
        

        h1=self.addHost('h1', ip='128.155.128.2/18')
        h2=self.addHost('h2', ip='128.155.192.2/19')
        h3=self.addHost('h3', ip='128.155.224.2/20')
        h4=self.addHost('h4', ip='128.155.240.2/20')
        
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
    net['h1'].cmd('route add default gw 128.155.128.1')
    net['h2'].cmd('route add default gw 128.155.192.1')
    net['h3'].cmd('route add default gw 128.155.224.1')
    net['h4'].cmd('route add default gw 128.155.240.1')
    
    info( 'Konfiguriere die Routing-Tabellen...\n' )
    
    net['r1'].cmd('ifconfig r1-eth0 128.155.128.1/18')
    net['r1'].cmd('ifconfig r1-eth1 10.0.0.1/30')
    
    net['r2'].cmd('ifconfig r2-eth0 128.155.192.1/19')
    net['r2'].cmd('ifconfig r2-eth1 10.0.0.2/30')
    net['r2'].cmd('ifconfig r2-eth2 10.0.1.1/30')
    
    net['r3'].cmd('ifconfig r3-eth0 10.0.1.2/30')
    net['r3'].cmd('ifconfig r3-eth1 128.155.224.1/20')
    net['r3'].cmd('ifconfig r3-eth2 128.155.240.1/23')
        
    net['r1'].cmd( 'ip route add 128.155.192.0/18 via 10.0.0.2' )
 
    net['r2'].cmd( 'ip route add 128.155.192.0/18 via 10.0.1.2' )
    net['r2'].cmd( 'ip route add 128.155.128.0/19 via 10.0.0.1' )

    net['r3'].cmd( 'ip route add 128.155.128.0/18 via 10.0.1.1' )

    info( 'Das Netzwerk ist nun einsatzbereit.\n' )
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel( 'info' )
    run()

