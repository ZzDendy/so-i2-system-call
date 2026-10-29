"""Simulasi pembacaan sensor kebun yang menulis data ke berkas log.

Dipakai sebagai subjek strace pada tugas I-2: program ini sengaja menyentuh
empat keluarga system call sekaligus (proses, berkas, memori, jaringan) supaya
jejaknya bisa dikelompokkan.
"""
import json
import os
import socket
import sys
import time

LOG = "results/sensor.log"
JUMLAH = 12
JEDA = 0.05


def baca_sensor():
    """Nilai sintetis: kelembapan tanah naik-turun seperti pembacaan nyata."""
    jam = time.time()
    return {
        "seq": int(jam * 1000) % 100000,
        "kelembapan": round(45 + 10 * ((jam % 30) / 30), 2),
        "suhu": round(27 + 3 * ((jam % 60) / 60), 2),
    }


def siapkan_berkas():
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    return open(LOG, "w", encoding="utf-8")


def kirim_ke_gateway(pesan):
    """Pengiriman singkat ke gateway lokal; gagal pun tidak menghentikan pencatatan."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(0.2)
        try:
            s.sendto(pesan.encode(), ("127.0.0.1", 9999))
        except OSError:
            pass


def main():
    f = siapkan_berkas()
    try:
        for i in range(JUMLAH):
            data = baca_sensor()
            data["seq"] = i
            baris = json.dumps(data) + "\n"
            f.write(baris)
            f.flush()
            os.fsync(f.fileno())
            if i % 3 == 0:
                kirim_ke_gateway(baris)
            time.sleep(JEDA)
    finally:
        f.close()
    print(f"selesai: {JUMLAH} rekaman ditulis ke {LOG}")


if __name__ == "__main__":
    sys.exit(main())
