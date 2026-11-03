#!/bin/bash
# No text over the splash, idempotent.   tools/quiet-boot.sh [host]
#  - kernel and systemd console moved to tty3 (never shown; the panel shows tty1), systemd status lines off
#  - no login prompt on tty1 (getty@tty1 masked) - it started ~13 s into boot and wrote over the picture; SSH is the way in
# Writes through the read-only overlay (overlayroot-chroot) and the read-only boot partition; applies from the next boot.
set -euo pipefail
HOST="${1:-pi@flightscope.local}"
ssh "$HOST" 'set -e
sudo systemctl mask getty@tty1.service >/dev/null 2>&1 || true
if grep -q overlayroot=tmpfs /proc/cmdline; then
  sudo overlayroot-chroot sh -c "ln -sf /dev/null /etc/systemd/system/getty@tty1.service"
  sync; sudo mount -o remount,ro /media/root-ro 2>/dev/null || echo "note: /media/root-ro left rw until the next reboot"
fi
C=/boot/firmware/cmdline.txt
if grep -q "console=tty1" $C || ! grep -q "systemd.show_status=false" $C; then
  ro=$(findmnt -no OPTIONS /boot/firmware | cut -d, -f1)
  [ "$ro" = ro ] && sudo mount -o remount,rw /boot/firmware
  sudo cp $C /boot/firmware/cmdline.txt.bak
  sudo sed -i "1 s/console=tty1/console=tty3/" $C
  grep -q "systemd.show_status=false" $C || sudo sed -i "1 s/\$/ systemd.show_status=false rd.udev.log_level=3 udev.log_priority=3/" $C
  sync; [ "$ro" = ro ] && sudo mount -o remount,ro /boot/firmware
  echo "cmdline: quiet boot from the next boot"
fi
[ $(wc -l < $C) -eq 1 ] || echo "WARNING: cmdline.txt is not one line"
cat $C; systemctl is-enabled getty@tty1 2>/dev/null || true'
