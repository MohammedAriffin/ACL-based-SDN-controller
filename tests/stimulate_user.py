import csv
import subprocess

CSV_PATH = "demo_flows.csv"
LOG_PATH = "simulation_results.log"

def run_flow(src_ip, dst_ip, protocol, port):
    if protocol == "ICMP":
        cmd = f"docker compose exec mininet mnexec -a {src_ip} ping -c 1 {dst_ip}"
    elif protocol == "TCP" and port:
        cmd = f"docker compose exec mininet mnexec -a {src_ip} nc -zv {dst_ip} {port}"
    else:
        return None
    print(f"\nRunning command: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    output = result.stdout if result.stdout else result.stderr
    print(output)
    return output

def main():
    with open(CSV_PATH) as f, open(LOG_PATH, "w") as logf:
        for row in csv.DictReader(f):
            output = run_flow(row['src_ip'], row['dst_ip'], row['protocol'], row['port'])
            log_line = f"{row['src_ip']}->{row['dst_ip']} {row['protocol']}:{row['port']}\n{output}\n"
            logf.write(log_line)

if __name__ == "__main__":
    try:
        main()
        print("\nSimulation completed. Results saved to simulation_results.log")
    except Exception as e:
        print(f"Simulation failed: {e}")
