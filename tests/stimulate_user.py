from mininet.net import Mininet
from mininet.node import Controller, RemoteController
from mininet.log import setLogLevel, info
from mininet.cli import CLI
import csv
import time

CSV_PATH = "/app/tests/demo_flows.csv"
LOG_PATH = "/app/tests/simulation_results.log"

def build_topology():
    info("*** Building Containernet topology ***\n")
    net = Mininet(controller=RemoteController)
    net.addController('c0', controller=RemoteController, ip='ryu', port=6653)

    # Add hosts (normal containers)
    h1 = net.addHost('h1', ip='10.0.1.10/24')
    h2 = net.addHost('h2', ip='10.0.1.11/24')
    h3 = net.addHost('h3', ip='10.0.2.10/24')
    h4 = net.addHost('h4', ip='10.0.2.11/24')
    ha = net.addHost('ha', ip='10.0.10.10/24')

    # Add simple user-space switch
    s1 = net.addSwitch('s1', protocols='OpenFlow13')

    # Connect all hosts
    for h in (h1, h2, h3, h4, ha):
        net.addLink(h, s1)

    net.start()
    info("*** Network started ***\n")

    # Start a web server in host ha
    ha.cmd('python3 -m http.server 80 >/dev/null 2>&1 &')
    return net


def run_flow(net, src_name, dst_ip, protocol, port=None):
    src = net.getNodeByName(src_name)
    if protocol == "ICMP":
        return src.cmd(f"ping -c 1 -W 2 {dst_ip}")
    elif protocol == "TCP" and port:
        return src.cmd(f"timeout 2 nc -zv {dst_ip} {port}")
    else:
        return "Unsupported protocol"


def simulate_flows(net):
    host_ip_map = {
        "10.0.1.10": "h1",
        "10.0.1.11": "h2",
        "10.0.2.10": "h3",
        "10.0.2.11": "h4",
        "10.0.10.10": "ha"
    }

    time.sleep(5)

    with open(CSV_PATH) as f, open(LOG_PATH, "w") as logf:
        logf.write("=== SDN ACL Controller Simulation Results ===\n\n")
        for row in csv.DictReader(f):
            src_name = host_ip_map.get(row['src_ip'])
            test_desc = f"Test: {row['role_src']}({row['src_ip']}) -> {row['role_dst']}({row['dst_ip']}) | {row['protocol']}"
            if row['port']:
                test_desc += f":{row['port']}"
            logf.write(f"\n{'='*60}\n{test_desc}\n{'='*60}\n")

            output = run_flow(net, src_name, row['dst_ip'], row['protocol'], row['port'])
            logf.write(f"{output}\n{'-'*60}\n\n")


def main():
    setLogLevel('info')
    net = build_topology()
    simulate_flows(net)
    net.stop()


if __name__ == "__main__":
    main()
