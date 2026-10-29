"""Memotong tangkapan layar ke area teks saja, supaya hemat tempat di laporan.

Batas atas dilewati karena berisi bilah judul dan bilah tab jendela terminal;
batas bawah dan kanan mengikuti piksel teks terakhir yang terdeteksi.
"""
import glob
import os

import numpy as np
from PIL import Image

MULAI = 100          # piksel dari atas: di bawah bilah judul dan bilah tab
AMBANG_TERANG = 330  # jumlah kanal RGB minimum agar dianggap teks
BUNTU = 20           # ruang kosong di bawah baris terakhir


def potong(path, keluar):
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(int)
    isi = a[MULAI:, :, :]
    terang = isi.sum(axis=2) > AMBANG_TERANG
    baris = np.where(terang.sum(axis=1) > 3)[0]
    kolom = np.where(terang.sum(axis=0) > 3)[0]
    if len(baris) == 0:
        raise SystemExit(f"tidak ada teks terdeteksi pada {path}")
    y1 = MULAI + min(isi.shape[0] - 1, baris[-1] + BUNTU)
    x1 = min(a.shape[1], kolom[-1] + 30)
    im.crop((0, MULAI, x1, y1)).save(keluar)
    return x1, y1 - MULAI


if __name__ == "__main__":
    for f in sorted(glob.glob("results/bukti/ss-*.png")):
        keluar = f.replace("ss-", "rapi-")
        x, t = potong(f, keluar)
        print(os.path.basename(f), f"-> {x}x{t}")
