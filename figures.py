"""Grafik untuk laporan I-2: komposisi system call per keluarga dan garis waktu."""
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

FONT = "DejaVu Sans"
OUT = "results"
WARNA = {
    "Proses": "#3B5B8C",
    "Berkas": "#B7791F",
    "Jaringan": "#2F6B3C",
    "Memori": "#A03B2C",
    "Lain-lain": "#7A7A7A",
}


def donat(d, path):
    urut = [k for k in ("Berkas", "Proses", "Memori", "Jaringan", "Lain-lain")
            if k in d["per_keluarga"]]
    nilai = [d["per_keluarga"][k]["panggilan"] for k in urut]
    total = sum(nilai)

    fig, ax = plt.subplots(figsize=(7.0, 3.6))
    baji, _ = ax.pie(
        nilai, labels=None,
        colors=[WARNA[k] for k in urut], startangle=90, counterclock=False,
        wedgeprops={"width": 0.46, "edgecolor": "white", "linewidth": 1.6})
    # Label persen hanya untuk irisan yang cukup lebar; sisanya dibaca dari legenda.
    for b, v in zip(baji, nilai):
        porsi = v / total * 100
        if porsi < 5:
            continue
        sudut = (b.theta1 + b.theta2) / 2
        import math
        x = 0.77 * math.cos(math.radians(sudut))
        y = 0.77 * math.sin(math.radians(sudut))
        ax.text(x, y, f"{porsi:.1f}%", ha="center", va="center", fontsize=8.4,
                fontfamily=FONT, color="white", fontweight="bold")
    ax.legend(baji, [f"{k} ({v} panggilan)" for k, v in zip(urut, nilai)],
              loc="center left", bbox_to_anchor=(1.0, 0.5), frameon=False,
              fontsize=8.2)
    ax.text(0, 0, f"{total}\nsystem call", ha="center", va="center",
            fontsize=9.5, fontfamily=FONT, fontweight="bold", linespacing=1.4)
    ax.set_title("Komposisi system call per keluarga", fontsize=10,
                 fontfamily=FONT, fontweight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=220, facecolor="white", bbox_inches="tight")
    plt.close(fig)


def waktu(d, path):
    """Batang mendatar waktu kernel per keluarga dalam mikrodetik."""
    urut = [k for k in ("Berkas", "Lain-lain", "Proses", "Memori", "Jaringan")
            if k in d["per_keluarga"]]
    nilai = [d["per_keluarga"][k]["detik"] * 1000 for k in urut]

    fig, ax = plt.subplots(figsize=(6.8, 2.8))
    b = ax.barh(urut[::-1], nilai[::-1], color=[WARNA[k] for k in urut[::-1]],
                edgecolor="white", height=0.55)
    for r in b:
        ax.annotate(f"{r.get_width():.2f} ms", (r.get_width(), r.get_y() + r.get_height() / 2),
                    textcoords="offset points", xytext=(4, 0), va="center",
                    fontsize=7.6, fontfamily=FONT)
    ax.set_xlabel("Waktu di kernel (ms)", fontfamily=FONT, fontsize=8.5)
    ax.tick_params(labelsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="x", color="#DDDDDD", linewidth=0.6)
    ax.set_axisbelow(True)
    ax.set_xlim(0, max(nilai) * 1.22)
    ax.set_title("Waktu yang dihabiskan di kernel per keluarga",
                 fontsize=10, fontfamily=FONT, fontweight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=220, facecolor="white")
    plt.close(fig)


def telanjang(d, path):
    """Top sepuluh syscall tersibuk, agar terlihat mana yang mendominasi."""
    semua = []
    for k, v in d["per_keluarga"].items():
        for nama, panggilan, galat, detik in v["syscall"]:
            semua.append((nama, panggilan, galat, k))
    semua.sort(key=lambda x: -x[1])
    atas = semua[:10]

    fig, ax = plt.subplots(figsize=(6.8, 3.2))
    nama = [x[0] for x in atas][::-1]
    nilai = [x[1] for x in atas][::-1]
    warna = [WARNA[x[3]] for x in atas][::-1]
    ax.barh(nama, nilai, color=warna, edgecolor="white", height=0.6)
    for i, v in enumerate(nilai):
        ax.annotate(str(v), (v, i), textcoords="offset points", xytext=(4, 0),
                    va="center", fontsize=7.4, fontfamily=FONT)
    ax.set_xlabel("Jumlah panggilan", fontfamily=FONT, fontsize=8.5)
    ax.tick_params(labelsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="x", color="#DDDDDD", linewidth=0.6)
    ax.set_axisbelow(True)
    ax.set_xlim(0, max(nilai) * 1.18)
    ax.set_title("Sepuluh system call paling sering dipanggil",
                 fontsize=10, fontfamily=FONT, fontweight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=220, facecolor="white")
    plt.close(fig)


def main():
    os.makedirs(OUT, exist_ok=True)
    with open("results/klasifikasi.json", encoding="utf-8") as f:
        d = json.load(f)
    donat(d, f"{OUT}/gambar-komposisi.png")
    waktu(d, f"{OUT}/gambar-waktu-kernel.png")
    telanjang(d, f"{OUT}/gambar-syscall-teratas.png")
    print("gambar:", [f for f in sorted(os.listdir(OUT)) if f.endswith(".png")])


if __name__ == "__main__":
    main()
