#!/bin/sh
# Regenere le dump memoire REEL + l'ISF Volatility 3 de F5.
# Aucune virtualisation materielle requise : QEMU en emulation (TCG).
#
# Prerequis hote (Debian/Ubuntu) :
#   apt install qemu-system-x86 busybox-static gcc xz-utils
#   # noyau bootable + ses symboles DWARF (memes versions) :
#   apt install linux-image-6.12.107+deb13-amd64 linux-image-6.12.107+deb13-amd64-dbg
#   # dwarf2json (binaire Go) :
#   curl -sL -o /usr/local/bin/dwarf2json \
#     https://github.com/volatilityfoundation/dwarf2json/releases/download/v0.9.0/dwarf2json-linux-amd64
#   chmod +x /usr/local/bin/dwarf2json
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
KVER=6.12.107+deb13-amd64
VMLINUZ=/boot/vmlinuz-$KVER
VMLINUX=/usr/lib/debug/boot/vmlinux-$KVER
OUT="$HERE/../../defi"
WORK=$(mktemp -d)

# cle/nonce partages avec F4 (shared_secret.py)
KEY=$(python3 -c "import sys;sys.path.insert(0,'$HERE/..');import shared_secret as s;print(s.KEY.hex())")
NONCE=$(python3 -c "import sys;sys.path.insert(0,'$HERE/..');import shared_secret as s;print(s.NONCE.hex())")

# 1. payload fileless (statique)
gcc -O2 -static -o "$WORK/stage2" "$HERE/stage2.c"
gcc -O2 -static -o "$WORK/loader" "$HERE/loader.c"

# 2. initramfs busybox
mkdir -p "$WORK/rootfs/bin"
cp /usr/bin/busybox "$WORK/rootfs/bin/"; cp "$WORK/stage2" "$WORK/loader" "$WORK/rootfs/bin/"
cat > "$WORK/rootfs/init" <<INIT
#!/bin/busybox sh
/bin/busybox --install -s /bin
mount -t proc proc /proc; mount -t sysfs sys /sys
mount -t devtmpfs dev /dev 2>/dev/null || { mkdir -p /dev; mknod /dev/null c 1 3; mknod /dev/console c 5 1; }
/bin/loader /bin/stage2 $KEY $NONCE &
sleep 3
echo "=====PAYLOAD_READY====="
while true; do sleep 5; done
INIT
chmod +x "$WORK/rootfs/init" "$WORK/rootfs/bin/"*
( cd "$WORK/rootfs" && find . | cpio -o -H newc 2>/dev/null | gzip -9 > "$WORK/initramfs.cpio.gz" )

# 3. boot QEMU-TCG + capture RAM physique (pmemsave) via QMP
qemu-system-x86_64 -m 256 -kernel "$VMLINUZ" -initrd "$WORK/initramfs.cpio.gz" \
  -append "console=ttyS0 panic=-1 quiet" -serial file:"$WORK/serial.log" \
  -qmp unix:"$WORK/qmp.sock",server,nowait -display none -no-reboot >/dev/null 2>&1 &
QPID=$!
for i in $(seq 1 60); do sleep 2; [ -S "$WORK/qmp.sock" ] && grep -q PAYLOAD_READY "$WORK/serial.log" 2>/dev/null && break; done
python3 - "$WORK" <<'PY'
import socket,json,sys
w=sys.argv[1]; s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM); s.connect(w+"/qmp.sock")
def rl(t=130):
    s.settimeout(t); b=b""
    while not b.endswith(b"\n"):
        d=s.recv(8192); b+=d
        if not d: break
    return b
rl(5); s.sendall(b'{"execute":"qmp_capabilities"}\n'); rl(5)
s.sendall(json.dumps({"execute":"pmemsave","arguments":{"val":0,"size":268435456,"filename":w+"/dump.raw"}}).encode()+b"\n"); rl(130)
s.sendall(b'{"execute":"quit"}\n')
PY
kill -9 $QPID 2>/dev/null || true

# 4. livrables : dump compresse + ISF
xz -9 -T0 -c "$WORK/dump.raw" > "$OUT/memoire.raw.xz"
mkdir -p "$OUT/symbols"
dwarf2json linux --elf "$VMLINUX" | xz -0 > "$OUT/symbols/linux-6.12.107-deb13.json.xz"
rm -rf "$WORK"
echo "genere: $OUT/memoire.raw.xz  +  $OUT/symbols/linux-6.12.107-deb13.json.xz"
