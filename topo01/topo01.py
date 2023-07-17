#!/usr/bin/python
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import Controller, Node
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink

class LinuxRouter(Node):
    def config(self, **params):
        super(LinuxRouter, self).config(**params)
        self.cmd('sysctl net.ipv4.ip_forward=1')

    def terminate(self):
        self.cmd('sysctl net.ipv4.ip_forward=0')
        super(LinuxRouter, self).terminate()



def topology():
    net = Mininet( controller=Controller, link=TCLink)

    info("*** Adding controller\n")
    c0 = net.addController( 'c0' )

    info("*** Adding hosts\n")
    h1 = net.addHost( 'h1', ip='10.0.1.2/24', defaultRoute='via 10.0.1.1' )
    h2 = net.addHost( 'h2', ip='10.0.2.2/24', defaultRoute='via 10.0.2.1' )

    info("*** Adding routers\n")
    r1 = net.addHost('r1', cls=LinuxRouter, ip='10.0.1.1/24')
    r2 = net.addHost('r2', cls=LinuxRouter, ip='10.0.2.1/24')

    info("*** Creating links\n")
    net.addLink( h1, r1, intfName1='h1-eth0', intfName2='r1-eth0', cls=TCLink, bw=100, delay='10ms' )
    net.addLink( r1, r2, intfName1='r1-eth1', intfName2='r2-eth0', cls=TCLink, bw=100, delay='10ms' )
    net.addLink( r2, h2, intfName1='r2-eth1', intfName2='h2-eth0', cls=TCLink, bw=100, delay='10ms' )

    info("*** Starting network\n")
    net.build()

    r1.cmd('ifconfig r1-eth0 10.0.1.1/24')
    r1.cmd('ifconfig r1-eth1 10.0.4.1/24')
    r2.cmd('ifconfig r2-eth1 10.0.2.1/24')
    r2.cmd('ifconfig r2-eth0 10.0.4.2/24')

    r1.cmd('ip route add 10.0.2.0/24 via 10.0.4.2')
    r2.cmd('ip route add 10.0.1.0/24 via 10.0.4.1')

    info("*** Running CLI\n")
    h1.cmd('xterm -T "h1 Terminal" &')
    h2.cmd('xterm -T "h2 Terminal" &')
    CLI( net )

    info("*** Stopping network\n")
    net.stop()

if __name__ == '__main__':
    setLogLevel( 'info' )
    topology()
