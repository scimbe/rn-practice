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
        #
        # Setup RIP Routers
        for i in range(2, 4):
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



#####################################################
##
##   Tests starting
##
#####################################################

def setup_module(module):
    global topo, net

    print("\n\n** %s: Setup Topology" % module.__name__)
    print("******************************************\n")

    print("Cleanup old Mininet runs")
    os.system('sudo mn -c > /dev/null 2>&1')

    thisDir = os.path.dirname(os.path.realpath(__file__))
    topo = NetworkTopo()

    net = Mininet(controller=None, topo=topo)
    net.start()

    # Starting Routers
    #
    for i in range(1, 4):
        net['r%s' % i].startRouter(thisDir)



def teardown_module(module):
    global net

    print("\n\n** %s: Shutdown Topology" % module.__name__)
    print("******************************************\n")

    # End - Shutdown network
    net.stop()


def test_router_running():
    global fatal_error
    global net

    # Skip if previous fatal error condition is raised
    if (fatal_error != ""):
        pytest.skip(fatal_error)

    print("\n\n** BECKE: The system is up and running! Remember you are working in /tmp/topotests/")
    print("******************************************\n")
    print("No routes are up time to setup some sniffer to watch the magic\n")
    CLI(net)
    for i in range(1, 4):
        net['r%s' % i].startStartRIPD(thisDir)
    print("Routes come up, but it needs some time\n")
    CLI(net)





def test_shutdown_check_stderr():
    global fatal_error
    global net

    # Skip if previous fatal error condition is raised
    if (fatal_error != ""):
        pytest.skip(fatal_error)

    if os.environ.get('TOPOTESTS_CHECK_STDERR') is None:
        pytest.skip('Skipping test for Stderr output and memory leaks')

    thisDir = os.path.dirname(os.path.realpath(__file__))

    print("\n\n** Verifing unexpected STDERR output from daemons")
    print("******************************************\n")

    net['r1'].stopRouter()

    log = net['r1'].getStdErr('ripd')
    if log:
        print("\nRIPd StdErr Log:\n" + log)
    log = net['r1'].getStdErr('zebra')
    if log:
        print("\nZebra StdErr Log:\n" + log)


if __name__ == '__main__':

    setLogLevel('debug')
    # To suppress tracebacks, either use the following pytest call or add "--tb=no" to cli
    # retval = pytest.main(["-s", "--tb=no"])
    retval = pytest.main(["-s"])
    sys.exit(retval)
