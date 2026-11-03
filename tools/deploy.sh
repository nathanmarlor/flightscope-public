#!/bin/bash
# rsync the app to the Pi and restart it.   tools/deploy.sh [host]
set -euo pipefail
HOST="${1:-pi@flightscope.local}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ssh "$HOST" "mkdir -p ~/flightscope/flightscope"
rsync -az --delete --exclude '__pycache__' "$ROOT/flightscope/" "$HOST:~/flightscope/flightscope/"
rsync -az "$ROOT/provision/flightscope.service" "$HOST:/tmp/flightscope.service"
rsync -az "$ROOT/provision/flightscope-bootsplash.service" "$HOST:/tmp/flightscope-bootsplash.service"
# read-only card (provision/make-readonly.sh): the rsync above only reached the RAM overlay - copy it to the real rootfs too (app stopped first: its open, replaced files keep the lower fs "busy" and it would not go back to ro)
ssh "$HOST" 'if grep -q overlayroot=tmpfs /proc/cmdline; then sudo systemctl stop flightscope; sudo rm -rf /run/fs-deploy; sudo cp -a ~/flightscope/flightscope /run/fs-deploy && sudo cp /tmp/flightscope.service /run/fs-deploy.service && sudo cp /tmp/flightscope-bootsplash.service /run/fs-deploy-boot.service && sudo overlayroot-chroot sh -c "rsync -a --delete --exclude __pycache__ /run/fs-deploy/ /home/pi/flightscope/flightscope/ && install -m644 /run/fs-deploy.service /etc/systemd/system/flightscope.service && install -m644 /run/fs-deploy-boot.service /etc/systemd/system/flightscope-bootsplash.service && mkdir -p /etc/systemd/system/sysinit.target.wants && ln -sf /etc/systemd/system/flightscope-bootsplash.service /etc/systemd/system/sysinit.target.wants/" ; sync; sudo mount -o remount,ro /media/root-ro 2>/dev/null; findmnt -no OPTIONS /media/root-ro | grep -q "^ro" && echo "written to the read-only rootfs (back to ro)" || echo "WARNING: /media/root-ro left read-write - reboot the Pi"; fi'
ssh "$HOST" 'sudo install -m644 /tmp/flightscope.service /etc/systemd/system/flightscope.service && sudo install -m644 /tmp/flightscope-bootsplash.service /etc/systemd/system/flightscope-bootsplash.service && sudo systemctl daemon-reload && sudo systemctl enable flightscope-bootsplash 2>/dev/null && sudo systemctl enable --now flightscope && sudo systemctl restart flightscope && sleep 1 && systemctl is-active flightscope'
