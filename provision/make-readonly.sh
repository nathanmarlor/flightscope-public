#!/bin/bash
# Make a flightscope card safe to switch off at any moment (the panel switch cuts power instantly).
#   Run on a Linux machine as root, card in the reader, Pi shut down:   sudo provision/make-readonly.sh [/dev/sda]
# - rootfs shrinks to ROOT_GB and runs read-only under overlayroot (writes go to RAM, gone at reboot)
# - a new ext4 partition LABEL=fsdata, mounted at /data, holds everything that must persist:
#     /data/logbook  <- ~/.cache/flightscope-logbook   /data/config <- ~/.config/flightscope
#     /data/cache    <- ~/.cache/flightscope (routes, photos)
#     /data/nm       bind on /etc/NetworkManager/system-connections, /data/netplan bind on /etc/netplan
#       (Wi-Fi joined from the setup screen survives a reboot)
# - /boot/firmware is mounted read-only
# Undo the overlay: on the Pi, sudo raspi-config nonint disable_overlayfs (or drop overlayroot=tmpfs from cmdline.txt here).
set -euo pipefail
DEV=${1:-/dev/sda}; S=""; [[ $DEV =~ [0-9]$ ]] && S=p     # /dev/loop0 -> /dev/loop0p1
P1=${DEV}${S}1; P2=${DEV}${S}2; P3=${DEV}${S}3
ROOT_GB=${ROOT_GB:-16}
M=/mnt/fs-root; D=/mnt/fs-data
command -v sfdisk >/dev/null && command -v resize2fs >/dev/null
[ -b "$P2" ] || { echo "no $P2"; exit 1; }
[ "$(blkid -s LABEL -o value "$P2")" = rootfs ] || { echo "$P2 is not a Pi OS rootfs"; exit 1; }
[ -b "$P3" ] && { echo "$P3 already exists - already done?"; exit 1; }
umount "$P1" "$P2" 2>/dev/null || true

echo "== shrink rootfs to ${ROOT_GB}G"
e2fsck -fy "$P2" || [ $? -le 1 ]
resize2fs "$P2" "${ROOT_GB}G"
dn=$(basename "$DEV"); pn=$(basename "$P2")
start=$(cat /sys/block/$dn/$pn/start)
size=$(( (ROOT_GB * 1024 + 64) * 2048 ))              # 64 MiB more than the filesystem, then grow it to fit
echo "$start,$size" | sfdisk --no-reread -N 2 "$DEV"
p3=$(( (start + size + 2047) / 2048 * 2048 ))
echo "$p3,,L" | sfdisk --no-reread --append "$DEV"
partprobe "$DEV" 2>/dev/null || blockdev --rereadpt "$DEV"; udevadm settle; sleep 1
resize2fs "$P2"; e2fsck -fy "$P2" || [ $? -le 1 ]

echo "== data partition"
mkfs.ext4 -q -F -L fsdata "$P3"
mkdir -p "$M" "$D"; mount "$P2" "$M"; mount "$P3" "$D"
trap 'umount "$D" "$M" 2>/dev/null || true' EXIT
H=$M/home/pi
move() {   # move dir $1 (on root) into $D/$2, leave a symlink to /data/$2
  mkdir -p "$D/$2"
  if [ -d "$1" ] && [ ! -L "$1" ]; then cp -a "$1/." "$D/$2/"; rm -rf "$1"; fi
  mkdir -p "$(dirname "$1")"; ln -sfn "/data/$2" "$1"; chown -h 1000:1000 "$1"; chown -R 1000:1000 "$D/$2"
}
move "$H/.cache/flightscope-logbook" logbook
move "$H/.config/flightscope" config
move "$H/.cache/flightscope" cache
for pair in "etc/NetworkManager/system-connections nm 700" "etc/netplan netplan 755"; do
  set -- $pair; mkdir -p "$D/$2"; chmod "$3" "$D/$2"
  cp -a "$M/$1/." "$D/$2/" 2>/dev/null || true
done
[ -s "$D/logbook/logbook.json" ] && echo "logbook: $(python3 -c "import json,sys; print(len(json.load(open(sys.argv[1]))))" "$D/logbook/logbook.json") planes moved"

echo "== fstab, boot read-only, overlay on"
F=$M/etc/fstab
sed -i -E 's#^(PARTUUID=[0-9a-f-]+-01\s+/boot/firmware\s+vfat\s+)defaults#\1defaults,ro#' "$F"
grep -q fsdata "$F" || cat >> "$F" <<'EOF'
LABEL=fsdata  /data  ext4  defaults,noatime,commit=5  0  2
/data/nm       /etc/NetworkManager/system-connections  none  bind,x-systemd.requires-mounts-for=/data  0  0
/data/netplan  /etc/netplan                            none  bind,x-systemd.requires-mounts-for=/data  0  0
EOF
mkdir -p "$M/data"
# netplan's generator runs before fstab mounts, so regenerate from /data/netplan before NetworkManager starts
cat > "$M/etc/systemd/system/flightscope-netplan.service" <<'EOF'
[Unit]
Description=Regenerate netplan from /data before NetworkManager
RequiresMountsFor=/etc/netplan
Before=NetworkManager.service
[Service]
Type=oneshot
ExecStart=/usr/sbin/netplan generate
[Install]
WantedBy=multi-user.target
EOF
ln -sf /etc/systemd/system/flightscope-netplan.service "$M/etc/systemd/system/multi-user.target.wants/flightscope-netplan.service"
mount "$P1" "$M/boot/firmware"
C=$M/boot/firmware/cmdline.txt
grep -q overlayroot=tmpfs "$C" || sed -i 's/^/overlayroot=tmpfs:recurse=0 /' "$C"     # recurse=0: leave /data and its binds as real mounts
cat "$C"; umount "$M/boot/firmware"
grep -q overlayroot "$M/var/lib/dpkg/status" || echo "WARNING: overlayroot package not installed on the card - the overlay won't start"
sync; echo "done"
