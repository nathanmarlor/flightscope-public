#!/bin/bash
# Flightscope Mk I - write Raspberry Pi OS Lite to a microSD and drop in the
# cloud-init provisioning + config.txt additions. Run as root.
#
#   sudo ./flash.sh /dev/sdX
#
set -euo pipefail
DEV="${1:?usage: flash.sh /dev/sdX}"
HERE="$(cd "$(dirname "$0")" && pwd)"
IMG="$HERE/rpios-lite.img"
NAME="$(basename "$DEV")"

[ "$(id -u)" = 0 ] || { echo "run as root"; exit 1; }
[ -f "$IMG" ] || { echo "missing $IMG"; exit 1; }
[ -b "$DEV" ] || { echo "$DEV is not a block device"; exit 1; }

# --- refuse anything that isn't a removable USB disk -------------------------
TRAN="$(lsblk -dno TRAN "$DEV")"; RM="$(lsblk -dno RM "$DEV")"; SIZE="$(lsblk -dno SIZE "$DEV")"
[ "$TRAN" = usb ] || { echo "refusing: $DEV transport is '$TRAN', not usb"; exit 1; }
[ "$RM" = 1 ]     || { echo "refusing: $DEV is not removable"; exit 1; }
if lsblk -no MOUNTPOINTS "$DEV" | grep -q .; then
  echo "refusing: $DEV has mounted partitions:"; lsblk "$DEV"; exit 1
fi
echo "target: $DEV  ($SIZE, $TRAN, removable)"

# --- write -------------------------------------------------------------------
echo "writing $(du -h "$IMG" | cut -f1) image..."
dd if="$IMG" of="$DEV" bs=4M status=progress conv=fsync
sync
partprobe "$DEV" 2>/dev/null || blockdev --rereadpt "$DEV"
udevadm settle
BOOT="/dev/${NAME}1"
for i in $(seq 1 20); do [ -b "$BOOT" ] && break; sleep 0.5; done
[ -b "$BOOT" ] || { echo "boot partition $BOOT did not appear"; exit 1; }

# --- provision the boot partition --------------------------------------------
MNT="$(mktemp -d)"
mount "$BOOT" "$MNT"
trap 'umount "$MNT" 2>/dev/null; rmdir "$MNT" 2>/dev/null' EXIT

echo "boot partition before:"; ls "$MNT" | tr '\n' ' '; echo
cp "$HERE/user-data"      "$MNT/user-data"
cp "$HERE/network-config" "$MNT/network-config"
[ -f "$MNT/meta-data" ] || : > "$MNT/meta-data"
# the GPS owns the UART: no serial console on it
sed -i -E 's/console=serial0,[0-9]+ ?//' "$MNT/cmdline.txt"
grep -q consoleblank "$MNT/cmdline.txt" || sed -i 's/$/ consoleblank=0 quiet loglevel=3 logo.nologo vt.global_cursor_default=0 video=HDMI-A-1:d video=HDMI-A-2:d/' "$MNT/cmdline.txt"
# no text over the splash: console on tty3 (the panel shows tty1), no systemd status lines; tools/quiet-boot.sh masks getty@tty1
sed -i "s/console=tty1/console=tty3/" "$MNT/cmdline.txt"
grep -q systemd.show_status "$MNT/cmdline.txt" || sed -i 's/$/ systemd.show_status=false rd.udev.log_level=3 udev.log_priority=3/' "$MNT/cmdline.txt"
# (HDMI off: the panel is DSI. Ethernet off too, once booted: tools/power-trim.sh)
# explicit panel overlay above, so stop the firmware probing for one as well (double-binds the I2C controller)
sed -i 's/^display_auto_detect=1/display_auto_detect=0/' "$MNT/config.txt"
if ! grep -q 'Flightscope Mk I' "$MNT/config.txt"; then
  cat "$HERE/config-append.txt" >> "$MNT/config.txt"
fi

echo "--- cmdline.txt ---"; cat "$MNT/cmdline.txt"
echo "--- config.txt tail ---"; tail -n 20 "$MNT/config.txt"
echo "--- user-data head ---"; head -n 6 "$MNT/user-data"
sync
umount "$MNT"; rmdir "$MNT"; trap - EXIT
udisksctl power-off -b "$DEV" 2>/dev/null || eject "$DEV" 2>/dev/null || true
echo
echo "DONE - card is safe to remove. First boot takes ~2-3 min while cloud-init installs packages."
echo "Then:  ssh pi@flightscope.local"
