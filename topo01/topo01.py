import os
import re
import sys
from subprocess import check_output

from sys import exit  # pylint: disable=redefined-builtin

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import Controller, Node
from mininet.cli import CLI
from mininet.log import setLogLevel, info, error
from mininet.link import TCLink
from mininet.link import Intf
from mininet.nodelib import NAT
from mininet.util import quietRun
from mininet.term import makeTerm

class LinuxRouter(Node):
    def config(self, **params):
        super(LinuxRouter, self).config(**params)
        self.cmd('sysctl net.ipv4.ip_forward=1')

    def terminate(self):
        self.cmd('sysctl net.ipv4.ip_forward=0')
        super(LinuxRouter, self).terminate()

# X11-Cookie-Handling

def distribute_x11_cookie(net):
    try:
        display = os.getenv('DISPLAY')
        if not display:
            error("DISPLAY variable not set. X11 forwarding might not work.\n")
            return

        cookie_output = check_output(f"xauth list {display}", shell=True).decode().strip().split()
        if cookie_output:
            cookie_value = cookie_output[-1]
            info(f"X11-Cookie: {cookie_value}\n")
            for host in net.hosts:
                host.cmd(f"xauth add {os.uname()[1]}/unix{display} MIT-MAGIC-COOKIE-1 {cookie_value}")
                info(f"X11-Cookie zu {host.name} hinzugefügt.\n")
        else:
            error("Kein X11-Cookie gefunden.\n")
    except Exception as e:
        error(f"Fehler beim Verteilen des X11-Cookies: {e}\n")


def checkIntf(intf):
    "Make sure intf exists and is not configured."
    config = quietRun('ip link show %s 2>/dev/null' % intf, shell=True)
    if not config:
        error('Error:', intf, 'does not exist!\n')
        exit(1)
    if 'state UP' in config:
        error('INFO:', intf, 'is up and may already be in use!\n')
        info("!!! Not sure if this is a problem - Should keep an eye on this\n")


def topology():
    net = Mininet(controller=Controller, link=TCLink, build=False)

    interface_name = os.getenv('INTERFACE', 'eth0')
    gateway_address = os.getenv('GATEWAY', '10.0.5.1')

    info("*** Adding controller\n")
    c0 = net.addController('c0')

    info("*** Adding hosts\n")
    h1 = net.addHost('h1')
    h2 = net.addHost('h2', ip='10.0.6.2/24', defaultRoute='via 10.0.6.1')

    info("*** Adding hosts and routers\n")
    r1 = net.addHost('r1', cls=LinuxRouter)
    r2 = net.addHost('r2', cls=LinuxRouter)

    info("*** Adding External Interface with Nat\n")
    s0 = net.addSwitch('s0')

    info("*** Creating links\n")
    net.addLink(h1, r1, intfName1='h1-eth1', intfName2='r1-eth0', cls=TCLink, bw=100, delay='10ms')
    net.addLink(r1, r2, intfName1='r1-eth1', intfName2='r2-eth0', cls=TCLink, bw=100, delay='10ms')
    net.addLink(r2, h2, intfName1='r2-eth1', intfName2='h2-eth0', cls=TCLink, bw=100, delay='10ms')
    net.addLink(h1, s0, intfName1='h1-eth0', intfName2='s0-eth0')

    net.build()

    h1.cmd('ifconfig h1-eth0 10.0.5.2/24')
    h1.cmd('ip route add default via 10.0.5.1')
    h1.cmd('ifconfig h1-eth1 10.0.1.2/24')
    h1.cmd('ip route add 10.0.6.0/24 via 10.0.1.1')

    r1.cmd('ifconfig r1-eth0 10.0.1.1/24')
    r1.cmd('ifconfig r1-eth1 10.0.4.1/24')
    r1.cmd('ip route add 10.0.6.0/24 via 10.0.4.2')

    r2.cmd('ifconfig r2-eth1 10.0.6.1/24')
    r2.cmd('ifconfig r2-eth0 10.0.4.2/24')
    r2.cmd('ip route add 10.0.1.0/24 via 10.0.4.1')
    r2.cmd('/usr/sbin/sshd')

    info('*** Connecting to hw intf: %s \n' % interface_name)
    checkIntf(interface_name)
    Intf(interface_name, node=s0)
    s0.cmd(f'ifconfig s0-eth0 {gateway_address}/24')
    s0.cmd('echo "1" > /proc/sys/net/ipv4/ip_forward')
    s0.cmd(f'iptables -t nat -A POSTROUTING -o {interface_name} -j MASQUERADE')

    distribute_x11_cookie(net)

    info("*** Running CLI\n")
    h1.cmd('dnsmasq --log-queries --no-daemon  --resolv-file=./resolve.conf --addn-hosts=./dnsmasq.hosts 2> dns.log &')
    h1.cmd(f'zutty -T {h1.name} &')
    h2.cmd(f'zutty -T {h2.name} &')
    CLI(net)

    info("*** Stopping network\n")
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    topology()
