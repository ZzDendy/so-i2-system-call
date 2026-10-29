"""Mengelompokkan system call dari keluaran strace ke empat keluarga.

Masukan: berkas ringkasan `strace -c`. Keluaran: tabel per keluarga plus
berkas JSON untuk laporan, sehingga angka di laporan selalu berasal dari
jejak yang benar-benar direkam.
"""
import json
import os
import re

RINGKASAN = "results/strace-ringkas.txt"
LOG = "results/sensor.log"
KELUAR = "results/klasifikasi.json"

# Pengelompokan mengikuti pembagian pada lembar tugas I-2.
KELUARGA = {
    "Proses": {
        "keterangan": "Membuat, menunggu, dan mengakhiri proses atau thread",
        "syscall": ["clone", "clone3", "fork", "vfork", "execve", "execveat", "exit",
                    "exit_group", "wait4", "waitid", "gettid", "set_tid_address",
                    "set_robust_list", "rseq", "getpid", "getppid", "gettid",
                    "kill", "tgkill", "rt_sigaction", "rt_sigprocmask", "rt_sigreturn",
                    "arch_prctl", "prlimit64"],
    },
    "Berkas": {
        "keterangan": "Membuka, membaca, menulis, dan mengatur berkas serta direktori",
        "syscall": ["openat", "open", "close", "read", "write", "pread64", "pwrite64",
                    "lseek", "fsync", "fdatasync", "ftruncate", "stat", "fstat",
                    "newfstatat", "lstat", "statx", "access", "faccessat", "readlink",
                    "readlinkat", "getdents64", "mkdir", "mkdirat", "unlink", "unlinkat",
                    "rename", "renameat", "chmod", "fchmod", "fcntl", "dup", "dup2",
                    "dup3", "getcwd", "ioctl", "poll", "ppoll", "epoll_create1",
                    "epoll_ctl", "epoll_wait", "select", "pselect6"],
    },
    "Jaringan": {
        "keterangan": "Membuat soket dan mengirim atau menerima data lewat jaringan",
        "syscall": ["socket", "connect", "bind", "listen", "accept", "accept4",
                    "sendto", "recvfrom", "sendmsg", "recvmsg", "sendmmsg", "recvmmsg",
                    "setsockopt", "getsockopt", "shutdown", "getsockname",
                    "getpeername"],
    },
    "Memori": {
        "keterangan": "Memetakan, melindungi, dan membebaskan ruang memori",
        "syscall": ["brk", "mmap", "munmap", "mprotect", "mremap", "madvise",
                    "mlock", "munlock"],
    },
    "Lain-lain": {
        "keterangan": "Waktu, identitas pengguna, dan keacakan yang tidak masuk empat "
                      "keluarga utama",
        "syscall": ["clock_nanosleep", "nanosleep", "clock_gettime", "gettimeofday",
                    "getuid", "geteuid", "getgid", "getegid", "getrandom", "futex",
                    "sched_yield", "uname", "sysinfo"],
    },
}


def baca_ringkasan(path):
    """Kembalikan {syscall: {'panggilan': n, 'galat': m, 'detik': s}}.

    strace -c menghilangkan kolom galat saat nilainya nol, sehingga satu baris
    bisa punya lima atau enam kolom.
    """
    hasil = {}
    with open(path, encoding="utf-8") as f:
        for baris in f:
            kolom = baris.split()
            if len(kolom) not in (5, 6) or not kolom[0][0].isdigit():
                continue
            nama = kolom[-1]
            if nama in ("syscall", "total"):
                continue
            try:
                detik = float(kolom[1])
                panggilan = int(kolom[3])
                galat = int(kolom[4]) if len(kolom) == 6 else 0
            except ValueError:
                continue
            hasil[nama] = {"detik": detik, "panggilan": panggilan, "galat": galat}
    return hasil


def keluarga_dari(nama):
    for keluarga, isi in KELUARGA.items():
        if nama in isi["syscall"]:
            return keluarga
    return "Lain-lain"


def main():
    syscalls = baca_ringkasan(RINGKASAN)
    if not syscalls:
        raise SystemExit(f"tidak ada data pada {RINGKASAN}")

    per_keluarga = {}
    for nama, data in syscalls.items():
        k = keluarga_dari(nama)
        masuk = per_keluarga.setdefault(k, {"panggilan": 0, "galat": 0, "detik": 0.0,
                                            "syscall": []})
        masuk["panggilan"] += data["panggilan"]
        masuk["galat"] += data["galat"]
        masuk["detik"] += data["detik"]
        masuk["syscall"].append((nama, data["panggilan"], data["galat"], data["detik"]))

    total_panggilan = sum(v["panggilan"] for v in syscalls.values())
    total_detik = sum(v["detik"] for v in syscalls.values())

    print(f"{'Keluarga':<12} {'Syscall':>8} {'Panggilan':>10} {'Galat':>7} {'Waktu (ms)':>11} {'Porsi':>7}")
    print("-" * 62)
    urutan = ["Proses", "Berkas", "Jaringan", "Memori", "Lain-lain"]
    for k in urutan:
        v = per_keluarga.get(k)
        if not v:
            continue
        porsi = v["panggilan"] / total_panggilan * 100
        print(f"{k:<12} {len(v['syscall']):>8} {v['panggilan']:>10} {v['galat']:>7} "
              f"{v['detik'] * 1000:>11.3f} {porsi:>6.1f}%")

    print("-" * 62)
    print(f"{'TOTAL':<12} {len(syscalls):>8} {total_panggilan:>10} "
          f"{sum(v['galat'] for v in syscalls.values()):>7} {total_detik * 1000:>11.3f}  100.0%")

    with open(LOG, encoding="utf-8") as f:
        rekaman = sum(1 for _ in f)

    hasil = {
        "total_panggilan": total_panggilan,
        "total_detik": total_detik,
        "jumlah_syscall_unik": len(syscalls),
        "rekaman_log": rekaman,
        "per_keluarga": {
            k: {"panggilan": v["panggilan"], "galat": v["galat"], "detik": v["detik"],
                "syscall": sorted(v["syscall"], key=lambda x: -x[1])}
            for k, v in per_keluarga.items()
        },
    }
    os.makedirs("results", exist_ok=True)
    with open(KELUAR, "w", encoding="utf-8") as f:
        json.dump(hasil, f, indent=2)
    print(f"\ntersimpan: {KELUAR}")


if __name__ == "__main__":
    main()
