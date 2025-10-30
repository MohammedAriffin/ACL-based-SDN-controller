from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel, info

def main():
    setLogLevel('info')
    
    net = Mininet(controller=RemoteController)
    net.addController('c0', controller=RemoteController, ip='ryu', port=6653)
    h1 = net.addHost('h1', ip='10.0.1.10/24')
    h2 = net.addHost('h2', ip='10.0.1.11/24')
    h3 = net.addHost('h3', ip='10.0.2.10/24')
    h4 = net.addHost('h4', ip='10.0.2.11/24')
    ha = net.addHost('ha', ip='10.0.10.10/24')
    s1 = net.addSwitch('s1', protocols='OpenFlow13')

    for h in (h1, h2, h3, h4, ha):
        net.addLink(h, s1)

    net.start()

    ha.cmd('python3 -m http.server 80 >/dev/null 2>&1 &')

if __name__ == '__main__':
    main()