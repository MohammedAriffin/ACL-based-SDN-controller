import csv
import subprocess
import time

CSV_PATH = "demo_flows.csv"
LOG_PATH = "simulation_results.log"

def run_flow(src_ip, dst_ip, protocol, port):
    """Execute network flow test from mininet container"""
    # Get the host name from IP (h1=10.0.1.10, h2=10.0.1.11, etc.)
    host_map = {
        "10.0.1.10": "h1",
        "10.0.1.11": "h2", 
        "10.0.2.10": "h3",
        "10.0.2.11": "h4",
        "10.0.10.10": "ha"
    }
    
    src_host = host_map.get(src_ip)
    if not src_host:
        return f"Unknown source IP: {src_ip}"
    
    if protocol == "ICMP":
        cmd = f"docker exec mininet-topo mn exec {src_host} ping -c 1 -W 2 {dst_ip}"
    elif protocol == "TCP" and port:
        cmd = f"docker exec mininet-topo mn exec {src_host} timeout 2 nc -zv {dst_ip} {port}"
    else:
        return None
    
    print(f"\nRunning command: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        output = result.stdout if result.stdout else result.stderr
        print(output)
        return output
    except subprocess.TimeoutExpired:
        return "Command timed out - likely blocked by ACL"
    except Exception as e:
        return f"Error: {str(e)}"

def main():
    print("Waiting for network topology to be ready...")
    time.sleep(5)
    
    with open(CSV_PATH) as f, open(LOG_PATH, "w") as logf:
        logf.write("=== SDN ACL Controller Simulation Results ===\n\n")
        for row in csv.DictReader(f):
            test_desc = f"Test: {row['role_src']}({row['src_ip']}) -> {row['role_dst']}({row['dst_ip']}) | {row['protocol']}"
            if row['port']:
                test_desc += f":{row['port']}"
            print(f"\n{'='*60}")
            print(test_desc)
            print('='*60)
            
            output = run_flow(row['src_ip'], row['dst_ip'], row['protocol'], row['port'])
            log_line = f"{test_desc}\n{output}\n{'-'*60}\n\n"
            logf.write(log_line)

if __name__ == "__main__":
    try:
        main()
        print("\n" + "="*60)
        print("Simulation completed. Results saved to simulation_results.log")
        print("="*60)
    except Exception as e:
        print(f"Simulation failed: {e}")
