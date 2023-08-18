#!/usr/bin/env python

#
# test_rip_topo1.py
# Part of NetDEF Topology Tests
#
# Copyright (c) 2017 by
# Network Device Education Foundation, Inc. ("NetDEF")
#
# Permission to use, copy, modify, and/or distribute this software
# for any purpose with or without fee is hereby granted, provided
# that the above copyright notice and this permission notice appear
# in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NETDEF DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NETDEF BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
#

"""
test_rip_topo1.py: Testing RIPv2

"""

import os
import re
import sys
import pytest
from time import sleep

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import Node, OVSSwitch, Host
from mininet.log import setLogLevel, info
from mininet.cli import CLI
from mininet.link import Intf

from functools import partial

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib import topotest
import lib.topotest 
fatal_error = ""


#####################################################
##
##   Network Topology Definition
##
#####################################################

class NetworkTopo(Topo):
    "RIP Topology 1"

    def build(self, **_opts):

        # Setup Routers
        router = {}
        #
        # Setup Main Router
        router[1] = topotest.addRouter(self, 'r1')
        #router[4] = topotest.addRouter(self, 'r1')
        #
        # Setup RIP Routers
        for i in range(2, 5):
            router[i] = topotest.addRouter(self, 'r%s' % i)
        #
        # Setup Switches
        switch = {}
        #
        # On main router
        # First switch is for a dummy interface (for local network)
        switch[1] = self.addSwitch('sw1', cls=topotest.LegacySwitch)
        self.addLink(switch[1], router[1], intfName2='r1-eth0')
        #
        # Switches for RIP
        # switch 2 switch is for connection to RIP router
        switch[2] = self.addSwitch('sw2', cls=topotest.LegacySwitch)
        self.addLink(switch[2], router[1], intfName2='r1-eth1')
        self.addLink(switch[2], router[2], intfName2='r2-eth0')
        # switch 3 is between RIP routers
        switch[3] = self.addSwitch('sw3', cls=topotest.LegacySwitch)
        self.addLink(switch[3], router[2], intfName2='r2-eth1')
        self.addLink(switch[3], router[3], intfName2='r3-eth1')
        # switch 4 is stub on remote RIP router
        switch[4] = self.addSwitch('sw4', cls=topotest.LegacySwitch)
        self.addLink(switch[4], router[3], intfName2='r3-eth0')
        
        self.addLink(switch[2], router[4], intfName2='r4-eth0')
        self.addLink(switch[3], router[4], intfName2='r4-eth1')
#####################################################
##
##   Tests starting
##
#####################################################

def startRIPD(net):
    thisDir = os.path.dirname(os.path.realpath(__file__))

    print("******** Start RIPD *************\n")   
    for i in range(1, 5):
        net['r%s' % i].startRIPD(thisDir)

def startBGPD(net):
    thisDir = os.path.dirname(os.path.realpath(__file__))

    print("******** Start BGP *************\n")   
    for i in range(1, 5):
        net['r%s' % i].startBGPD(thisDir)
  
          
        
def run():
    topo = NetworkTopo()
    print("******************************************\n")

    print("Cleanup old Mininet runs")
    os.system('sudo mn -c > /dev/null 2>&1')

    thisDir = os.path.dirname(os.path.realpath(__file__))

    net = Mininet(controller=None, topo=topo)
    net.start()

    # Starting Routers
    #
    for i in range(1, 5):
        net['r%s' % i].startRouter(thisDir)
    print("******** Router up and running *************\n")   
    CLI(net) 
    startRIPD(net)
    startBGPD(net)
    CLI(net)
    print("\n\n** %s: Shutdown Topology")
    print("******************************************\n")

    for i in range(1, 5):
        net['r%s' % i].stopRouter()
    # End - Shutdown network
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run()
