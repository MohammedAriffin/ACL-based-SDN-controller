# Docker Setup Guide for ACL-based SDN Controller

This guide explains how to run the ACL-based SDN Controller in Docker containers.

## Overview

The application consists of three main services:
1. **Ryu Controller** - The SDN controller implementing ACL policies
2. **Mininet** - Network topology simulator with virtual hosts and switches
3. **Simulator** - Automated test runner for verifying ACL rules

## Prerequisites

- Docker Desktop installed and running
- Docker Compose (included with Docker Desktop)

## Quick Start

### 1. Build and Start All Services

```bash
docker compose up --build
```

This will:
- Start the Ryu SDN controller
- Create the Mininet network topology with 5 hosts (h1, h2, h3, h4, ha)
- Run the automated simulation tests

### 2. View Logs

To see logs from a specific service:

```bash
# Ryu controller logs
docker compose logs -f ryu

# Mininet topology logs
docker compose logs -f mininet

# Simulator logs
docker compose logs -f simulator
```

### 3. Access Mininet CLI

To interact with the Mininet network directly:

```bash
docker exec -it mininet-topo bash
# Then inside the container:
# mn
```

### 4. Manual Testing

Execute commands on specific hosts:

```bash
# Ping from h1 to h2
docker exec mininet-topo mn exec h1 ping -c 3 10.0.1.11

# Test HTTP access from guest (h3) to admin (ha)
docker exec mininet-topo mn exec h3 curl -I http://10.0.10.10

# Test SSH access (should be blocked for guests)
docker exec mininet-topo mn exec h3 nc -zv 10.0.10.10 22
```

## Network Configuration

### Host IP Addresses

| Host | IP Address    | Role    |
|------|---------------|---------|
| h1   | 10.0.1.10/24  | Student |
| h2   | 10.0.1.11/24  | Student |
| h3   | 10.0.2.10/24  | Guest   |
| h4   | 10.0.2.11/24  | Guest   |
| ha   | 10.0.10.10/24 | Admin   |

### ACL Rules Implemented

1. **ICMP Block**: Blocks ping from h1 (10.0.1.10) to h2 (10.0.1.11)
2. **Student → Admin Block**: Denies all traffic from student network (10.0.1.x) to admin (10.0.10.10)
3. **Guest Restrictions**:
   - Allows HTTP (port 80) traffic
   - Blocks FTP (port 21) and SSH (port 22)
   - Denies all other traffic by default

## Simulation Results

The simulator automatically tests these ACL rules and saves results to `tests/simulation_results.log`.

View the results:

```bash
docker exec test-simulator cat /simulator/simulation_results.log
```

Or from your host machine:

```bash
type tests\simulation_results.log
```

## Stopping the Services

```bash
# Stop all services
docker compose down

# Stop and remove all data
docker compose down -v
```

## Troubleshooting

### Controller not connecting

Check if the Ryu controller is running:

```bash
docker compose ps
docker compose logs ryu
```

### Mininet issues

Restart the Mininet container:

```bash
docker compose restart mininet
```

### Network connectivity problems

Ensure the custom bridge network is created:

```bash
docker network ls | findstr sdn
```

### View all container IPs

```bash
docker network inspect acl-based-sdn-controller_sdn_network
```

## Development

### Modifying ACL Rules

Edit `controller/acl_controller.py` and restart the Ryu service:

```bash
docker compose restart ryu
```

### Changing Network Topology

Edit `topology/acl_topology.py` and restart Mininet:

```bash
docker compose restart mininet
```

### Adding Test Cases

Edit `tests/demo_flows.csv` and run the simulator:

```bash
docker compose restart simulator
```

## Architecture

```
┌─────────────────┐
│  Ryu Controller │ (Port 6653 - OpenFlow)
│   172.18.0.2    │
└────────┬────────┘
         │
         │ OpenFlow Protocol
         │
┌────────▼────────┐
│    Mininet      │
│  Network Topo   │ (h1, h2, h3, h4, ha + s1 switch)
│   172.18.0.3    │
└────────┬────────┘
         │
         │ Docker exec commands
         │
┌────────▼────────┐
│   Simulator     │ (Runs test scenarios)
│   172.18.0.4    │
└─────────────────┘
```

## Useful Commands

```bash
# Rebuild a specific service
docker compose build ryu

# View running containers
docker compose ps

# Access container shell
docker exec -it mininet-topo bash

# Follow all logs
docker compose logs -f

# Clean up everything
docker compose down -v --remove-orphans
```
