#!/usr/bin/python
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import Controller, Node
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink
from mininet.link import Intf
from mininet.nodelib import NAT

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
    h1 = net.addHost( 'h1', ip='10.0.1.2/24', defaultRoute='via 10.0.5.1' )
    h2 = net.addHost( 'h2', ip='10.0.2.2/24', defaultRoute='via 10.0.2.1' )

    info("*** Adding External Interface with Nat\n")
    #natParams = { 'ip' : '%s/24' % '192.168.0.1' }

    #nat = net.addHost('nat', cls=NAT, subnet='192.168.0.0/24', inetIntf='nat-eth0', localIntf='nat-eth1')
    #net.addLink(nat, s0, intfName1='nat-eth1')

    info("*** Adding routers\n")
    r1 = net.addHost('r1', cls=LinuxRouter, ip='10.0.1.1/24')
    r2 = net.addHost('r2', cls=LinuxRouter, ip='10.0.2.1/24')

    info("*** Creating links\n")
    net.addLink( h1, r1, intfName1='h1-eth0', intfName2='r1-eth0', cls=TCLink, bw=100, delay='10ms' )
    net.addLink( r1, r2, intfName1='r1-eth1', intfName2='r2-eth0', cls=TCLink, bw=100, delay='10ms' )
    net.addLink( r2, h2, intfName1='r2-eth1', intfName2='h2-eth0', cls=TCLink, bw=100, delay='10ms' )

    info("*** Starting network with nat on switch s0\n")
    s0 = net.addSwitch('s0')
    Intf('enp0s5', node=s0) ## do not forget to setup for env
    net.addLink(h1, s0, intfName1='h1-eth1', intfName2='s0-eth0')

    net.build()

    r1.cmd('ifconfig r1-eth0 10.0.1.1/24')
    r1.cmd('ifconfig r1-eth1 10.0.4.1/24')
    r2.cmd('ifconfig r2-eth1 10.0.2.1/24')
    r2.cmd('ifconfig r2-eth0 10.0.4.2/24')
    h1.cmd('ifconfig h1-eth1 10.0.5.2/24')
    s0.cmd('ifconfig s0-eth0 10.0.5.1/24')

    h1.cmd('ip route add 10.0.2.0/24 via 10.0.1.1')
    h1.cmd('ip route add 0.0.0.0/0 via 10.0.5.1')

    r1.cmd('ip route add 10.0.2.0/24 via 10.0.4.2')
    r2.cmd('ip route add 10.0.1.0/24 via 10.0.4.1')

    s0.cmd('ip route add 10.0.1.0/24 via 10.0.5.2')
    s0.cmd('echo "1" > /proc/sys/net/ipv4/ip_forward')
    s0.cmd('iptables -t nat -A POSTROUTING -o enp0s5 -j MASQUERADE')

    info("*** Running CLI\n")
    h1.cmd('dnsmasq --log-queries --no-daemon  --resolv-file=./resolve.conf --addn-hosts=./dnsmasq.hosts 2> dns.log &')
    h1.cmd('xterm -xrm \'XTerm.vt100.allowTitleOps: false\' -T \'h1 Terminal\' &')
    h2.cmd('xterm -xrm \'XTerm.vt100.allowTitleOps: false\' -T \'h2 Terminal\' &')
    CLI( net )

    info("*** Stopping network\n")
    net.stop()

if __name__ == '__main__':
    setLogLevel( 'info' )
    topology()
