#!/bin/bash
set -e

echo "[run_all] Starting Ryu controller..."
ryu-manager controller/acl_controller.py --ofp-tcp-listen-port 6653 &

sleep 8

#echo "[run_all] Starting Mininet topology..."
#python3 topology/acl_topology.py &

#sleep 10

echo "[run_all] Running simulator..."
python3 tests/stimulate_user.py || true

echo "[run_all] Completed. Tail logs..."
tail -f /dev/null
