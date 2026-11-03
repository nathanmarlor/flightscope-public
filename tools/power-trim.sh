#!/bin/bash
# Small power savings on the Pi, idempotent.   tools/power-trim.sh [host]
#  - Ethernet: NetworkManager leaves eth0 unmanaged and eth-off.service puts the link down (the PHY powers down)
#  - HDMI: both HDMI connectors disabled on the kernel command line (video=HDMI-A-n:d; the DSI panel is DSI-1)
#    (HDMI audio is already off: snd_bcm2835.enable_hdmi=0)
# Writes through the read-only overlay (overlayroot-chroot) and the read-only boot partition; reboot to apply HDMI.
set -euo pipefail
HOST="${1:-pi@flightscope.local}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
scp -q "$ROOT/provision/eth-off.service" "$ROOT/provision/nm-no-eth.conf" "$HOST:/tmp/"
ssh "$HOST" 'set -e
sudo install -m644 /tmp/nm-no-eth.conf /etc/NetworkManager/conf.d/90-no-eth.conf
sudo install -m644 /tmp/eth-off.service /etc/systemd/system/eth-off.service
sudo systemctl daemon-reload; sudo systemctl enable --now eth-off.service; sudo nmcli general reload conf 2>/dev/null || true
if grep -q overlayroot=tmpfs /proc/cmdline; then
  sudo cp /tmp/nm-no-eth.conf /tmp/eth-off.service /run/
  sudo overlayroot-chroot sh -c "install -m644 /run/nm-no-eth.conf /etc/NetworkManager/conf.d/90-no-eth.conf && install -m644 /run/eth-off.service /etc/systemd/system/eth-off.service && ln -sf /etc/systemd/system/eth-off.service /etc/systemd/system/multi-user.target.wants/eth-off.service"
  sync; sudo mount -o remount,ro /media/root-ro 2>/dev/null || echo "note: /media/root-ro left rw until the next reboot"
fi
C=/boot/firmware/cmdline.txt
if ! grep -q "video=HDMI-A-1:d" $C; then
  ro=$(findmnt -no OPTIONS /boot/firmware | cut -d, -f1)
  [ "$ro" = ro ] && sudo mount -o remount,rw /boot/firmware
  sudo cp $C /boot/firmware/cmdline.txt.bak
  sudo sed -i "1 s/\$/ video=HDMI-A-1:d video=HDMI-A-2:d/" $C
  sync; [ "$ro" = ro ] && sudo mount -o remount,ro /boot/firmware
  echo "cmdline: HDMI off from the next boot"
fi
[ $(wc -l < $C) -eq 1 ] || echo "WARNING: cmdline.txt is not one line"
ip -br link show eth0; tr " " "\n" < $C | grep video='
