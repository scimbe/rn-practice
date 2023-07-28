#!/usr/bin/python

from mininet.net import Mininet
from mininet.node import Node, OVSKernelSwitch, Controller
from mininet.link import TCLink
from mininet.log import setLogLevel
from mininet.cli import CLI

def create_bottleneck_scenario():
    net = Mininet(controller=Controller, link=TCLink, switch=OVSKernelSwitch)

    # Hinzufügen der Controller-Komponente
    net.addController('c0')

    # Hinzufügen der Nodes
    h1 = net.addHost('h1')
    h2 = net.addHost('h2')
    r1 = net.addHost('r1')
    r2 = net.addHost('r2')
    h3 = net.addHost('h3')
    h4 = net.addHost('h4')

    # Hinzufügen der Switches
    s1 = net.addSwitch('s1')
    s2 = net.addSwitch('s2')

    # Links konfigurieren
    net.addLink(h1, s1, bw=10, delay='5ms')
    net.addLink(h2, s1, bw=10, delay='5ms')
    net.addLink(s1, r1, bw=10, delay='5ms')
    net.addLink(r1, s2, bw=10, delay='5ms')
    net.addLink(s2, r2, bw=10, delay='5ms')
    net.addLink(h3, s2, bw=10, delay='5ms')
    net.addLink(h4, s2, bw=10, delay='5ms')

    # Starten des Netzwerks
    net.start()

    # Namensauflösung ermöglichen
#    net.pingAll()

    # Eingabeaufforderung öffnen
    CLI(net)

    # Netzwerk stoppen
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    create_bottleneck_scenario()
