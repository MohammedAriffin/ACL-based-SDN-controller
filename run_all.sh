#!/bin/bash
set -e

echo "Starting Ryu controller..."
ryu-manager controller/acl_controller.py &

sleep 5  # wait for controller to initialize

echo "Starting Mininet topology..."
python3 topology/acl_topology.py &

sleep 5  # wait for topology to initialize

echo "Running user simulation..."
python3 tests/simulate_users.py

wait  # wait for background processes to finish
