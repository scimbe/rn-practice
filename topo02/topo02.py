#!/usr/bin/python

"""
Copyright 2023-present Martin Becke 
# SPDX-License-Identifier: Apache-2.0

Dependencies:
    Work with this setub base on the mininet image and dnsmasq netsurf whois nmap snapd curl
    $ sudo apt install dnsmasq netsurf whois nmap snapd curl
    $ sudo snap install searchsploit
"""

from mininet.net import Mininet
from mininet.node import Node, OVSKernelSwitch, Controller, RemoteController

from mininet.cli import CLI
from mininet.link import Link, TCLink, Intf
from mininet.topo import Topo
from mininet.log import setLogLevel, info
from mininet.node import Node
from typing import List, Dict, Tuple, Union
from mininet.term import makeTerm
import os


N=2
'''
    Dynamic setup of a much bigger network

    h0--s1--r1---r2----s2---h3
         |             |    
        h1             h2   
'''

class RTopo(Topo):

    def build(self, **_opts):     
        h = [0]*(N+2)		# h[0], h[N+1] are a special case
        r = [0]*(N+1)
        s = [0]*(N+1)
        # we need some router
        for i in range(1, N+1):
            r[i] = self.addHost( 'r{}'.format(i) )
        # we need some switche
        for i in range(1, N+1):
            s[i] = self.addSwitch( 's{}'.format(i) )     
        # now do the same for hosts
        for i in range(0, N+2):
            h[i] = self.addHost( 'h{}'.format(i) )
            
        self.addLink( h[0], s[1], intfName1 = 'h0-eth0', intfName2 = 's1-eth1')		
        self.addLink( r[1], s[1], intfName1 = 'r1-eth0', intfName2 = 's1-eth0')	
        self.addLink( h[N+1], s[N], intfName1 = 'h{}-eth0'.format(N+1), intfName2 = 's{}-eth1'.format(N))	
        self.addLink( r[N], s[N], intfName1 = 'r{}-eth0'.format(N), intfName2 = 's{}-eth3'.format(N))	
        
        self.addLink( h[1], s[1], intfName1 = 'h0-eth0', intfName2 = 'r1-eth2')		
        self.addLink( h[N], s[N], intfName1 = 'h{}-eth0'.format(N), intfName2 = 's{}-eth0'.format(N))	
        
        #for i in range(1,N+1):		# 
        #    self.addLink(h[i], r[i], intfName1='h{}-eth0'.format(i), intfName2='r{}-eth0'.format(i))
        
        # Route to router, here we add bottlenecks
        for i in range(1,N):
            self.addLink(r[i], r[i+1], intfName1 = 'r{}-eth2'.format(i), intfName2='r{}-eth1'.format(i+1), cls=TCLink, bw=10, delay='0.1ms')


def  setup_router_ip(net):
    for i in range(1,N+1):
        rname = 'r{}'.format(i)
        r=net[rname]
        if0name='{}-eth0'.format(rname)
        ip0addr='10.0.{}.1'.format(10*i)
        r.cmd('ifconfig {} {}/24'.format(if0name, ip0addr))
        if1name='{}-eth1'.format(rname)
        ip1addr='10.0.{}.2'.format(i-1)		# correct for i==0
        r.cmd('ifconfig {} {}/24'.format(if1name, ip1addr))
        if2name='{}-eth2'.format(rname)
        if i != N:
            ip2addr='10.0.{}.1'.format(i)    
        else:
           ip2addr='10.0.{}.1'.format((N+1)*10)
        
        r.cmd('ifconfig {} {}/24'.format(if2name, ip2addr))  
        r.cmd('sysctl net.ipv4.ip_forward=1')
        ifacelist = r.intfList()
        for iface in ifacelist:
            if iface != 'lo': r.cmd('sysctl net.ipv4.conf.{}.rp_filter=0'.format(iface))

def setup_host_ip(net):
    # h0, h N + 1 is special
    h0 = net['h0']
    h0.cmd('ifconfig h0-eth0 10.0.10.10/24')
    h0.cmd('ip route add to default via 10.0.10.1')
   
   
    h1 = net['h1']
    h1.cmd('ifconfig h0-eth0 10.0.10.11/24')
    h1.cmd('ip route add to default via 10.0.10.1')
    
    hn = net['h{}'.format(N+1)]
    hn.cmd('ifconfig {}-eth0 10.0.{}.11/24'.format(hn, 10*(N)))
    hn.cmd('ip route add to default via 10.0.{}.1'.format((10*(N))))
    
    hn = net['h{}'.format(N)]
    hn.cmd('ifconfig {}-eth0 10.0.{}.10/24'.format(hn, 10*(N)))
    hn.cmd('ip route add to default via 10.0.{}.1'.format((10*(N))))
        
        

def setup_route(net):
     for k in range(0,N+1):
          for i in range(1,N+1):
             rname = 'r{}'.format(i)
             r=net[rname]
             if0name='{}-eth1'.format(rname)
             if1name='{}-eth2'.format(rname)
	   	
             if i > k:
                  r.cmd('ip route add 10.0.{}.0/24 via 10.0.{}.1 dev {}'.format((10*(k)), ((i-1)), if0name))
             if i < (k):
                  r.cmd('ip route add 10.0.{}.0/24 via 10.0.{}.2 dev {}'.format((10*(k)), (i), if1name))  
 

def  setup_webServerOnH1(net):
    h1 = net['h1']
    h1.cmd('python3 ~/rn-practical/topo02/startHTTPD.py &')      
                  
def run():
    rtopo = RTopo()
    net = Mininet(topo = rtopo, link=TCLink, autoSetMacs = True)
    net.start()
    
    # Setup Router IP adresses
    setup_router_ip(net)
    setup_host_ip(net)
    setup_route(net)

    setup_webServerOnH1(net)
    makeTerm((net['r1']))
    makeTerm((net['h0']))
    makeTerm((net['h1'])) 
    makeTerm((net['h{}'.format(N)]))
    makeTerm((net['h{}'.format(N+1)]))
    CLI( net)
    

    net.stop()    
    
if __name__ == '__main__':
    setLogLevel('info')
    run()
