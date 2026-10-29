#!/usr/bin/env bash
# Bukti terminal asli untuk laporan I-2: strace pada program simulasi sensor.
# Prompt, gema perintah, dan keluaran berasal dari bash dan strace yang asli.
set -u

DIR=${1:?butuh folder kerja}
OUT=${2:?butuh folder keluaran}
FIFO=/tmp/shotest/i2.fifo
mkdir -p "$OUT"
rm -f "$FIFO"; mkfifo "$FIFO"

cd "$DIR" || exit 1

io.elementary.terminal -n -w "$DIR" -x "bash --noprofile --rcfile $HOME/.bashrc -i < $FIFO" \
  > /dev/null 2>&1 &
TERM_PID=$!
sleep 4

exec 3>"$FIFO"

tangkap() {
  sleep 0.8
  gdbus call --session --dest org.gnome.Shell.Screenshot \
    --object-path /org/gnome/Shell/Screenshot \
    --method org.gnome.Shell.Screenshot.ScreenshotWindow \
    true false false "$OUT/ss-$1.png" > /dev/null 2>&1
  echo "  -> ss-$1.png"
}

ketik() { printf '%s\n' "$1" >&3; }

ketik 'clear'
sleep 1
tangkap "01-prompt"

# 1. program yang diuji
ketik 'head -20 sensor_log.py'
tangkap "02-program"

# 2. ringkasan system call
ketik 'strace -f -c -o results/strace-ringkas.txt python3 sensor_log.py'
sleep 2
tangkap "03-jalankan"

ketik 'head -12 results/strace-ringkas.txt'
tangkap "04-ringkasan"

# 3. syscall yang menulis berkas log
ketik 'grep -E "openat.*sensor\.log|write\(3" results/strace-lengkap.txt | head -6'
tangkap "05-tulis-berkas"

# 4. pemanggilan fsync
ketik 'grep -c "fsync" results/strace-lengkap.txt'
tangkap "06-fsync"

# 5. pemanggilan jaringan
ketik 'grep "sendto" results/strace-lengkap.txt | head -2'
tangkap "07-jaringan"

# 6. bukti peralihan mode: waktu kernel vs total
ketik 'tail -2 results/strace-ringkas.txt'
tangkap "08-total"

# 7. klasifikasi
ketik 'python3 klasifikasi.py'
sleep 2
tangkap "09-klasifikasi"

# 8. struktur kernel
ketik 'uname -r && grep -c "^#define __NR_" /usr/include/x86_64-linux-gnu/asm/unistd_64.h'
tangkap "10-kernel"

exec 3>&-
sleep 1
kill "$TERM_PID" 2>/dev/null
rm -f "$FIFO"
echo "selesai: $(ls -1 "$OUT"/ss-*.png | wc -l) tangkapan layar"
