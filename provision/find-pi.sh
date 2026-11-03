#!/bin/bash
# Find the flightscope Pi on the local /24. mDNS first, ARP sweep second.
set -u
if ip=$(getent hosts flightscope.local 2>/dev/null | awk '{print $1}') && [ -n "$ip" ]; then
  echo "mdns  flightscope.local -> $ip"; exit 0
fi
net=$(ip -4 -o addr show wlan0 | awk '{print $4}' | cut -d/ -f1 | cut -d. -f1-3)
for i in $(seq 1 254); do ping -c1 -W1 "$net.$i" >/dev/null 2>&1 & done; wait
ip neigh | grep -iE 'dc:a6:32|e4:5f:01|d8:3a:dd|b8:27:eb|2c:cf:67|28:cd:c1' | awk '{print "arp   " $1, $5}' | grep -v "$(hostname -I | awk '{print $1}')"
