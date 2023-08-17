#!/usr/bin/python3
# copyright 2021 Peter Dordal and 2023 Martin Becke
# licensed under the Apache 2.0 license
# type hinting passes mypy, except for the imported modules

"""router topology example

chain of N routers between two hosts; here is the diagram for N=3

    h0---r1---r2---r3---h4
         |    |    |
        h1   h2   h3

In this version we add h4 to the right of r3,
with the same IPv4 address as h0. We then let BGP figure out how to get to that IPv4 address

Diagram of interfaces and IPv4 addresses of r2, with neighbors r1, r3.

   r1:r1-eth2--------r2-eth1:r2:r2-eth2-----------r3-eth1:r3
     10.0.1.1       10.0.1.2    10.0.2.1          10.0.2.2
     
Subnets are 10.0.1 (r1--r2) and 10.0.2 (r2--r3)
Last byte (host byte) is 2 on the left and 1 on the right
   10.0.?.?-r1-10.0.1.1
   10.0.1.2-r2-10.0.2.1
   10.0.2.2-r3-10.0.?.?
ri-eth1 is on the left and ri-eth2 is on the right. ri-eth0 connects to hi. 

The "primary" IP address of ri is 10.0.i.1

The interface to the hosts is 10.0.10i.1
the host hi is 10.0.10i.10

"""

# mn --custom router.py --topo rtopo

from mininet.net import Mininet
from mininet.node import Node, OVSKernelSwitch, Controller, RemoteController
#from mininet.node import Node, Host, OVSSwitch, OVSKernelSwitch, Controller, RemoteController, DefaultController
from mininet.cli import CLI
from mininet.link import Link, TCLink, Intf
from mininet.topo import Topo
from mininet.log import setLogLevel, info
from mininet.node import Node
from typing import List, Dict, Tuple, Union
import os
from helper import *

N=5

BGP = True

ANYCAST = True

class RTopo(Topo):

    def build(self, **_opts):     # special names?
        # We're using arrays h[] and r[] instead of specific names h0, r0, etc. Note h[0] is the old h0, etc.
        h = [0]*(N+2)		# h[0], h[N+1] are a special case
        r = [0]*(N+1)
        for i in range(1, N+1):
            r[i] = self.addHost( 'r{}'.format(i) )
        # now do the same for h0-hN, with range(0,N+1)   
        for i in range(0, N+2):
            h[i] = self.addHost( 'h{}'.format(i) )
            
        # Set up the the ri--hi links; the interface names are ri-eth0 and hi-eth0
        self.addLink( h[0], r[1], intfName1 = 'h0-eth0', intfName2 = 'r1-eth1')		# special case: h[0]--r[1] link
        self.addLink( h[N+1], r[N], intfName1 = 'h{}-eth0'.format(N+1), intfName2 = 'r{}-eth2'.format(N))		# special case: h[0]--r[1] link
        
        for i in range(1,N+1):		# 
            self.addLink(h[i], r[i], intfName1='h{}-eth0'.format(i), intfName2='r{}-eth0'.format(i))

        # now set up the links r1--r2--...--rN, by joining each r[i] and r[i+1]
        for i in range(1,N):
            self.addLink(r[i], r[i+1], intfName1 = 'r{}-eth2'.format(i), intfName2='r{}-eth1'.format(i+1))
            
            
def run():
    rtopo = RTopo()
    net = Mininet(topo = rtopo, link=TCLink, autoSetMacs = True)
    net.start()

    # now record all the router nodes and their interfaces
    ifdict = {}
    BGPnodelist = []		
    for i in range(1, N+1):
        nodename = 'r{}'.format(i)
        node = net[nodename]
        BGPnodelist.append(node)
        
    print('BGPnodelist:', BGPnodelist)
    
    ndict = neighbordict(BGPnodelist)
    
    # print('neighbordict:')
    # dumpdict(ndict)
    
    # set up the ri IPv4 addresses        
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
        if i<N:
            ip2addr='10.0.{}.1'.format(i)
        elif ANYCAST:
            ip2addr='10.0.0.2'
        if i<N or ANYCAST:
            r.cmd('ifconfig {} {}/24'.format(if2name, ip2addr))
        r.cmd('sysctl net.ipv4.ip_forward=1')
        r.cmd('usermod -a -G frr,frrvty root')
        rp_disable(r)
        
    addrdict = addressdict(BGPnodelist)
    
    #print('addrdict:')
    #dumpdict(addrdict)
    
    # set up a map from ri to the corresponding AS numbers. Can also be set manually.
    ASdict = {}
    for i in range(1, N+1):
        nodename = 'r{}'.format(i)
        ASdict[nodename] = 1000*i
    
        
    # now set up the hi IPv4 addresses, for i in range(1, N+1) (that is, h1-hN)
    # Each hi should also have a default route: 
    # For h2 this is "ip route add to default via 10.0.20.1"
    for i in range(1, N+1):
        hname = 'h{}'.format(i)			# 'h1', 'h2', etc
        hi = net[hname]
        hi.cmd('ifconfig {}-eth0 10.0.{}.10/24'.format(hname, 10*i))
        hi.cmd('ip route add to default via 10.0.{}.1'.format(10*i))
    
    # now set up h0 and (at least if ANYCAST is requested) h[N+1]
    h0 = net['h0']
    h0.cmd('ifconfig h0-eth0 10.0.0.1/24')
    h0.cmd('ip route add to default via 10.0.0.2')

    hmax=net['h{}'.format(N+1)]
    if ANYCAST: 
        hmax.cmd('ifconfig h{}-eth0 10.0.0.1/24'.format(N+1))
        hmax.cmd('ip route add to default via 10.0.0.2')
        
    # now we build zebra.conf

    zconflist = []
    
    for r in BGPnodelist:
        zconf = create_zebra_conf(r, ndict)
        zconflist.append(zconf)

    bgpconflist = []
    # now we build bgpd.conf
    for r in BGPnodelist:
        bgpconf = create_bgpd_conf(r, ndict, addrdict, ASdict)
        bgpconflist.append(bgpconf)
        

    # now we start up the routing stuff on each router
    for r in BGPnodelist:
        r.cmd('/usr/sbin/sshd')		# not really needed
        start_zebra(r)
        start_bgpd(r)
    
    CLI( net)

    for r in BGPnodelist:
        stop_zebra(r)
        stop_bgpd(r)
        
    net.stop()

    for zconf in zconflist:
        print('removing file {}'.format(zconf))
        os.remove(zconf)
    for bgpconf in bgpconflist:
        print('removing file {}'.format(bgpconf))
        os.remove(bgpconf)

    os.system('stty erase {}'.format(chr(8)))
            
def dumpdict(d):
    print('='*30)
    for pair in d:
        (n,i) = pair
        print('node {} interface {} goes to {}'.format(n,i,d[pair]))
    print('='*30)
        
DIRPREFIX=os.getcwd()

setdirprefix(DIRPREFIX)   	# share the prefix with the bgphelpers.py module 
    
def start_zebra(r : Node):
    name = '{}'.format(r)
    dir='{}/{}/'.format(DIRPREFIX, name)
    config = dir + 'zebra.conf'
    pid =  dir + 'zebra.pid'
    log =  dir + 'zebra.log'
    zsock=  dir + 'zserv.api'
    # r.cmd('> {}'.format(log))			# this creates the file with the wrong permissions
    r.cmd('rm -f {}'.format(pid))    	# we need to delete the pid file
    r.cmd('/usr/lib/frr/zebra --daemon --config_file {} --pid_file {} --socket {}'.format(config, pid, zsock))

def stop_zebra(r : Node):
    name = '{}'.format(r)
    dir='{}/{}/'.format(DIRPREFIX, name)
    pidfile =  dir + 'zebra.pid'
    f = open(pidfile)
    pid = int(f.readline())
    zsock=  dir + 'zserv.api'
    r.cmd('kill {}'.format(pid))
    r.cmd('rm {}'.format(zsock))
 
    
# not used here 
def start_ripd(r):
    name = '{}'.format(r)
    dir='{}/{}/'.format(DIRPREFIX, name)
    config = dir + 'ripd.conf'
    zsock  = dir + 'zserv.api'
    pid    = dir + 'ripd.pid'
    r.cmd('/usr/lib/frr/ripd --daemon --config_file {} --pid_file {} --socket {}'.format(config, pid, zsock))

def stop_ripd(r):
    name = '{}'.format(r)
    dir='{}/{}/'.format(DIRPREFIX, name)
    pidfile =  dir + 'ripd.pid'
    f = open(pidfile)
    pid = int(f.readline())
    r.cmd('kill {}'.format(pid))

def start_bgpd(r : Node):
    name = '{}'.format(r)
    dir='{}/{}/'.format(DIRPREFIX, name)
    config = dir + 'bgpd.conf'
    zsock  = dir + 'zserv.api'
    pid    = dir + 'bgpd.pid'
    r.cmd('/usr/lib/frr/bgpd --daemon --config_file {} --pid_file {}  --socket {}'.format(config, pid, zsock))
     
def stop_bgpd(r : Node):
    name = '{}'.format(r)
    dir='{}/{}/'.format(DIRPREFIX, name)
    pidfile =  dir + 'bgpd.pid'
    f = open(pidfile)
    pid = int(f.readline())
    r.cmd('kill {}'.format(pid))
    

# For some examples we need to disable the default blocking of forwarding of packets with no reverse path
def rp_disable(host : Node):
    # ifaces = host.cmd('ls /proc/sys/net/ipv4/conf')
    # ifacelist = ifaces.split()    # default is to split on whitespace
    ifacelist = host.intfList()
    for iface in ifacelist:
       if iface != 'lo': host.cmd('sysctl net.ipv4.conf.{}.rp_filter=0'.format(iface))
    #print 'host', host, 'iface list:',  ifacelist

setLogLevel('debug')		# or 'info'
run()

