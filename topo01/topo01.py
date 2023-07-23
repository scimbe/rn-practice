"""
Copyright 2023-present Martin Becke 
# SPDX-License-Identifier: Apache-2.0

Dependencies:
    Work with this setub base on the mininet image and dnsmasq netsurf whois nmap snapd curl
    $ sudo apt install dnsmasq netsurf whois nmap snapd curl
    $ sudo snap install searchsploit
"""

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# @author Martin Becke scimbe@becke.net

#!/usr/bin/python

import re
import sys

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

def checkIntf( intf ):
    "Make sure intf exists and is not configured."
    config = quietRun( 'ifconfig %s 2>/dev/null' % intf, shell=True )
    if not config:
        error( 'Error:', intf, 'does not exist!\n' )
        exit( 1 )
    ips = re.findall( r'\d+\.\d+\.\d+\.\d+', config )
    if ips:
        error( 'INFO:', intf, 'has an IP address,'
               'and is probably in use!\n' )
        info("!!! Not sure if this is a problem - Should keep an eye on this\n")

def topology():
    net = Mininet( controller=Controller, link=TCLink)

    with open('interface.txt', 'r') as file:
        values = file.readlines()
        interface_name = values[0].rstrip()
        gateway_address = values[1].rstrip()

    info("*** Adding controller\n")
    c0 = net.addController( 'c0' )

    info("*** Adding hosts\n")
    h1 = net.addHost( 'h1')
  
    h2 = net.addHost( 'h2', ip='10.0.6.2/24', defaultRoute='via 10.0.6.1' )

    info("*** Adding hosts and routers\n")
    r1 = net.addHost('r1', cls=LinuxRouter)

    r2 = net.addHost('r2', cls=LinuxRouter)

    info("*** Adding External Interface with Nat\n")
    s0 = net.addSwitch('s0')
       
    info("*** Creating links\n")
    net.addLink( h1, r1, intfName1='h1-eth1', intfName2='r1-eth0', cls=TCLink, bw=100, delay='10ms' )
    net.addLink( r1, r2, intfName1='r1-eth1', intfName2='r2-eth0', cls=TCLink, bw=100, delay='10ms' )
    net.addLink( r2, h2, intfName1='r2-eth1', intfName2='h2-eth0', cls=TCLink, bw=100, delay='10ms' )

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
#    r2.cmd('while true; do rm -f /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc -l 1234 >/tmp/f; done &')


    info( '*** Connecting to hw intf: %s \n' % str(interface_name) ) # Testsystem "enp0s5"  #"enp0s5"  # 
    checkIntf( str(interface_name) )
    Intf( str(interface_name) , node=s0) 
    s0.cmd('ifconfig s0-eth0 10.0.5.1/24')
    s0.cmd('ip route add 10.0.1.0/24 via 10.0.5.2')
    s0.cmd('echo "1" > /proc/sys/net/ipv4/ip_forward')
    s0.cmd('iptables -t nat -A POSTROUTING -o ' +  str(interface_name) + ' -j MASQUERADE')

    info("*** Running CLI\n")
    h1.cmd('dnsmasq --log-queries --no-daemon  --resolv-file=./resolve.conf --addn-hosts=./dnsmasq.hosts 2> dns.log &')
#    h1.cmd('xterm -xrm \'XTerm.vt100.allowTitleOps: false\' -T \'h1 (Host 1)\' &')
#    h2.cmd('xterm -xrm \'XTerm.vt100.allowTitleOps: false\' -T \'h2 (Host 2)\' &')
    makeTerm(h1)
    makeTerm(h2)
    CLI( net )

    info("*** Stopping network\n")
    net.stop()

if __name__ == '__main__':
    setLogLevel( 'info' )
    topology()
    
# Backlog
    #natParams = { 'ip' : '%s/24' % '192.168.0.1' }

    #nat = net.addHost('nat', cls=NAT, subnet='192.168.0.0/24', inetIntf='nat-eth0', localIntf='nat-eth1')
    #net.addLink(nat, s0, intfName1='nat-eth1') 
    
    

