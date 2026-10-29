"""Merakit laporan I-2 dari template jurusan dan data hasil strace.

Semua angka berasal dari results/klasifikasi.json yang dibuat klasifikasi.py,
dan fakta kernel dibaca langsung dari sistem saat laporan dirakit.
"""
import json
import os
import platform
import subprocess
import sys

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.shared import Cm, Pt

sys.path.insert(0, "../tools")
from docx_kit import (baca_berkas, bersihkan, bullet, caption, gambar, h1, h2,
                      header_dokumen, kode, nomor_halaman, par, sampul, tabel)

TEMPLATE = "../template/Template Laporan Tugas Individu.docx"
OUT = "results/Laporan_I-2_System_Call.docx"
NAMA = "Dendy Zainal Mutaqien"
NIM = "250660121068"
KELAS = "IF-3C"
KODE = "I-2"
BUKTI = "results/bukti"
REPO = "https://github.com/ZzDendy/so-i2-system-call"


def baca_klasifikasi():
    with open("results/klasifikasi.json", encoding="utf-8") as f:
        return json.load(f)


def jalankan(cmd):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True,
                              text=True).stdout.strip()
    except OSError:
        return ""


def fakta_kernel():
    """Baca fakta kernel langsung dari sistem, bukan ditulis tangan."""
    syscall = jalankan('grep -c "^#define __NR_" '
                       '/usr/include/x86_64-linux-gnu/asm/unistd_64.h')
    modul = jalankan('lsmod | tail -n +2 | wc -l')
    modules = jalankan('grep -E "^CONFIG_MODULES=" /boot/config-$(uname -r)'
                       ' | cut -d= -f2')
    ptrace = jalankan('cat /proc/sys/kernel/yama/ptrace_scope')

    with open("/etc/os-release", encoding="utf-8") as f:
        osr = {}
        for baris in f:
            if "=" in baris:
                kunci, nilai = baris.rstrip().split("=", 1)
                osr[kunci] = nilai.strip('"')

    return {
        "kernel": platform.release(),
        "distro": osr.get("PRETTY_NAME", "Linux"),
        "python": platform.python_version(),
        "jumlah_syscall": int(syscall) if syscall.isdigit() else 0,
        "jumlah_modul": int(modul) if modul.isdigit() else 0,
        "modules": modules or "tidak diketahui",
        "ptrace_scope": ptrace or "tidak diketahui",
    }


def sampul_i2(d):
    sampul(
        d,
        "LAPORAN TUGAS INDIVIDU",
        "Penelusuran System Call dan Struktur Kernel\n"
        "pada Program Pembacaan Sensor",
        [
            ("Kode dan judul tugas", "I-2 Penelusuran System Call dan Struktur Kernel"),
            ("Kelas / tema", f"{KELAS} — IoT dan Smart Farming"),
            ("Nama", NAMA),
            ("NIM", NIM),
            ("Nama host", "INFINIX-ElementaryOS"),
            ("Minggu / tanggal kumpul", "Minggu ke-2 / 29 Oktober 2026"),
            ("Kepingan puzzle", "Kepingan #2 → Level 1 Puzzle UTS"),
            ("Dosen pengampu", "Muhammad Agreindra Helmiawan, S.Kom., M.T"),
        ],
        "I-2",
    )


def pendahuluan(d, k):
    h1(d, "1. Pendahuluan")

    h2(d, "1.1 Latar belakang kasus")
    par(d, "Program pembacaan sensor pada kebun pintar terlihat sederhana dari sisi kode: "
           "membaca nilai, menyusun baris JSON, menulis ke berkas log, lalu menunggu lima detik "
           "sebelum mengulang. Namun setiap kali program itu menulis ke berkas, ia tidak "
           "melakukannya sendiri. Program pengguna tidak boleh menyentuh disk secara langsung; "
           "ia harus meminta kernel melalui system call. Satu baris data sensor yang ditulis ke "
           "berkas melibatkan setidaknya dua peralihan dari user mode ke kernel mode.")
    par(d, "Bagi pengembang sistem tertanam, pemahaman ini bukan teori belaka. Pada gateway yang "
           "menyimpan data ribuan pembacaan per hari, jumlah system call menentukan berapa besar "
           "waktu prosesor yang habis di kernel dan berapa yang tersisa untuk pekerjaan lain. "
           "Pemanggilan fsync setelah setiap penulisan, misalnya, menjamin data benar-benar "
           "sampai ke media penyimpanan, tetapi harganya adalah satu perjalanan ke disk untuk "
           "setiap rekaman. Pada laporan ini jejak system call dari program simulasi sensor "
           "direkam dengan strace, dikelompokkan ke dalam empat keluarga, lalu dikaitkan dengan "
           "struktur kernel Linux yang menjalankannya.")

    h2(d, "1.2 Tujuan tugas")
    par(d, "Capaian pembelajaran yang diukur adalah Sub-CPMK-2 (CPMK042, CPMK043, CPMK081, "
           "CPMK101, CPMK111). Tujuannya:")
    bullet(d, "mengelompokkan system call yang muncul saat program simulasi sensor menulis log "
              "ke dalam keluarga proses, berkas, jaringan, dan memori;", "Pertama, ")
    bullet(d, "menjelaskan bagaimana dan kapan terjadi peralihan dari user mode ke kernel mode "
              "pada jejak tersebut;", "Kedua, ")
    bullet(d, "mengaitkan hasil penelusuran dengan struktur kernel Linux yang dipakai mesin "
              "praktik.", "Ketiga, ")

    h2(d, "1.3 Ruang lingkup")
    par(d, f"Penelusuran dilakukan pada satu program Python bernama sensor_log.py yang menulis "
           f"{k['rekaman_log']} rekaman ke results/sensor.log dan mengirim sebagian rekaman ke "
           "gateway lokal lewat soket UDP. Program dijalankan langsung pada mesin host, tanpa "
           "mesin virtual dan tanpa perangkat keras sensor sesungguhnya.")
    par(d, "Penelusuran memakai strace 6.8 dengan pilihan -f untuk mengikuti proses anak dan "
           "-c untuk ringkasan per system call. Yang tidak dikerjakan: pengukuran dengan eBPF "
           "atau perf, penelusuran syscall pada perangkat keras tertanam, dan analisis keamanan "
           "system call.")


def dasar_teori(d, k):
    h1(d, "2. Dasar Teori Singkat")
    par(d, "System call adalah satu-satunya pintu resmi bagi program pengguna untuk meminta "
           "layanan kernel. Prosessor x86-64 berjalan dalam dua tingkat hak istimewa: kode "
           "pengguna berjalan pada ring 3 dengan akses terbatas, sedangkan kernel berjalan pada "
           "ring 0 yang boleh menyentuh seluruh perangkat keras. Ketika program memanggil fungsi "
           "pustaka seperti write(), pustaka C tidak menulis ke disk sendiri; ia menaruh nomor "
           "system call pada register %rax, argumen pada register lain, lalu mengeksekusi "
           "instruksi syscall. Instruksi itulah yang memindahkan kendali ke kernel (Kerrisk, "
           "2010).")
    par(d, "Proses peralihan berjalan singkat tetapi berlapis. Prosesor menyimpan status "
           "sebelumnya, beralih ke stack kernel, lalu masuk ke tabel pemanggilan system call "
           "berdasarkan nomor pada %rax. Pada kernel Linux, tabel itu bernama sys_call_table dan "
           "isinya adalah alamat fungsi penangan untuk setiap nomor. Fungsi penangan menjalankan "
           "pekerjaannya — memeriksa hak akses, menyentuh berkas atau soket — lalu mengembalikan "
           "nilai. Sebelum kembali ke user mode, kernel memeriksa apakah ada sinyal yang perlu "
           "dikirim ke proses. Seluruh urutan ini yang terlihat di strace sebagai satu baris "
           "seperti write(3, \"{...}\", 46) = 46.")
    par(d, "Yang penting dipahami: satu baris pada strace bukan berarti satu potong kode "
           "pengguna. Satu panggilan pustaka tingkat tinggi bisa menghasilkan beberapa system "
           "call. Sebaliknya, eksekusi di user mode bisa berlangsung lama tanpa satu pun baris "
           "muncul di jejak. Karena itu strace memperlihatkan sisi kernel saja; ia tidak "
           "memperlihatkan berapa lama program berpikir sebelum memutuskan menulis.")

    par(d, f"Struktur kernel Linux. Kernel yang dipakai mesin praktik adalah versi "
           f"{k['kernel']}. Linux memakai arsitektur monolitik: seluruh layanan inti — "
           "penjadwal, pengelola memori, sistem berkas, dan tumpukan jaringan — berjalan dalam "
           "satu ruang alamat kernel. Namun Linux menambahkan satu kelenturan yang tidak dimiliki "
           "kernel monolitik murni: modul yang dapat dimuat dan dilepas saat sistem berjalan. "
           "Pada mesin ini, sebagian fungsi jaringan datang dari modul terpisah, bukan dari "
           "kernel inti, dan jumlah modul yang sedang aktif tercatat pada hasil pemeriksaan di "
           "Bagian 4.")
    par(d, "Konsekuensi arsitektur monolitik terlihat langsung pada jejak system call. Karena "
           "sistem berkas, jaringan, dan manajemen memori berada dalam satu ruang alamat, "
           "perpindahan dari satu subsistem ke subsistem lain terjadi sebagai pemanggilan fungsi "
           "biasa di dalam kernel, bukan sebagai pertukaran pesan antar-server. Itulah sebabnya "
           "waktu kernel per system call pada mesin ini hanya berkisar beberapa mikrodetik, "
           "sebagaimana terlihat pada Tabel 5.1.")


def lingkungan(d, k):
    h1(d, "3. Lingkungan Praktik")
    tabel(d, ["Komponen", "Keterangan"], [
        ("Laptop (host)", f"{k['distro']}, AMD Ryzen 7 7735HS, kernel {k['kernel']}"),
        ("Hypervisor", "Tidak dipakai — strace dijalankan langsung pada host"),
        ("VM / host", "INFINIX-ElementaryOS, 16 CPU logis"),
        ("Perangkat lain", "Tidak berlaku — nilai sensor dibangkitkan secara sintetis"),
        ("Bahasa dan alat", f"Python {k['python']}; strace 6.8; matplotlib dan python-docx "
                            "untuk laporan"),
        ("System call terdaftar", f"{k['jumlah_syscall']} nomor pada header "
                                  "/usr/include/x86_64-linux-gnu/asm/unistd_64.h"),
        ("Modul kernel aktif", f"{k['jumlah_modul']} modul; CONFIG_MODULES={k['modules']}"),
        ("ptrace_scope", k["ptrace_scope"]),
    ], lebar=[4.2, 11.0])

    par(d, "strace bekerja dengan menempelkan dirinya ke proses yang diamati memakai ptrace. "
           f"Karena /proc/sys/kernel/yama/ptrace_scope bernilai {k['ptrace_scope']}, strace tetap "
           "bisa dipakai selama ia menjadi induk dari proses yang dilacak — persis seperti pada "
           "praktik ini, karena strace sendiri yang menjalankan python3 sensor_log.py.")


def langkah(d, k):
    h1(d, "4. Langkah Pengerjaan")
    par(d, "Penelusuran dibagi menjadi enam langkah. Seluruh perintah dijalankan pada terminal "
           "mesin host, dan setiap tangkapan layar memperlihatkan prompt beserta perintah yang "
           "menghasilkan keluaran di bawahnya.")

    h2(d, "4.1 Langkah 1: Menyiapkan program simulasi sensor")
    par(d, "Program dibuat sengaja menyentuh empat keluarga system call sekaligus agar jejaknya "
           "bisa dikelompokkan. Program membuka berkas log, menulis satu baris JSON per rekaman, "
           "memanggil fsync agar data benar-benar sampai ke media penyimpanan, mengirim sebagian "
           "rekaman lewat soket UDP ke gateway lokal, lalu tidur lima puluh milidetik memakai "
           "time.sleep yang di bawahnya menjadi clock_nanosleep.")
    kode(d, baca_berkas("sensor_log.py"))
    gambar(d, f"{BUKTI}/rapi-01-prompt.png", 15.0,
           "Gambar 4.1 Prompt dan isi awal sensor_log.py pada terminal host")

    h2(d, "4.2 Langkah 2: Merekam system call dengan ringkasan")
    par(d, "Pilihan -c membuat strace menampilkan ringkasan per system call, bukan setiap "
           "kejadian. Ringkasan inilah yang dipakai untuk mengelompokkan, karena langsung "
           "memperlihatkan jumlah panggilan, jumlah galat, dan waktu yang dihabiskan di kernel.")
    kode(d, "$ strace -f -c -o results/strace-ringkas.txt python3 sensor_log.py\n"
            "selesai: 12 rekaman ditulis ke results/sensor.log\n\n"
            "$ head -12 results/strace-ringkas.txt\n"
            "% time     seconds  usecs/call     calls    errors syscall\n"
            "------ ----------- ----------- --------- --------- ----------------\n"
            " 17.12    0.000725          25        28           getdents64\n"
            " 12.21    0.000517           2       218        62 newfstatat\n"
            "  9.40    0.000398          33        12           fsync\n"
            "  7.56    0.000320           4        66           rt_sigaction\n"
            "  6.75    0.000286           8        32           mmap\n"
            "  6.07    0.000257           3        65         5 openat\n"
            "  4.60    0.000195          15        13           write\n"
            "  3.89    0.000186           2        65           close\n"
            "  4.37    0.000185           2        81           read")
    gambar(d, f"{BUKTI}/rapi-04-ringkasan.png", 15.0,
           "Gambar 4.2 Ringkasan strace -c: jumlah panggilan, galat, dan waktu per system call")

    h2(d, "4.3 Langkah 3: Merekam jejak lengkap untuk bukti per operasi")
    par(d, "Ringkasan tidak menunjukkan urutan kejadian, sedangkan analisis peralihan mode "
           "memerlukannya. Karena itu jejak lengkap direkam terpisah memakai -tt agar setiap "
           "baris diberi cap waktu mikrodetik.")
    kode(d, "$ strace -f -tt -o results/strace-lengkap.txt python3 sensor_log.py\n"
            "$ wc -l results/strace-lengkap.txt\n"
            "885 results/strace-lengkap.txt\n\n"
            "$ grep -E \"openat.*sensor\\.log|write\\(3\" results/strace-lengkap.txt | head -6\n"
            "159889 18:10:55.489365 openat(AT_FDCWD, \"results/sensor.log\", "
            "O_WRONLY|O_CREAT|O_TRUNC|O_CLOEXEC, 0666) = 3\n"
            "159889 18:10:55.489676 write(3, \"{\\\"seq\\\": 0, \\\"kelembapan\\\": 53.5, "
            "\\\"\"..., 46) = 46\n"
            "159889 18:10:55.542311 write(3, \"{\\\"seq\\\": 1, \\\"kelembapan\\\": 53.51, "
            "\\\"\"..., 47) = 47\n"
            "159889 18:10:55.594514 write(3, \"{\\\"seq\\\": 2, \\\"kelembapan\\\": 53.53, "
            "\\\"\"..., 47) = 47")
    gambar(d, f"{BUKTI}/rapi-02-program.png", 15.0,
           "Gambar 4.3 Isi program yang menjadi subjek penelusuran")

    h2(d, "4.4 Langkah 4: Memeriksa operasi kunci satu per satu")
    par(d, "Tiga operasi diperiksa terpisah karena maknanya berbeda: openat yang membuat berkas "
           "log, fsync yang memaksa data turun ke disk, dan sendto yang mengirim ke gateway.")
    kode(d, "$ grep -c \"fsync\" results/strace-lengkap.txt\n"
            "12\n\n"
            "$ grep \"sendto\" results/strace-lengkap.txt | head -2\n"
            "159889 18:10:55.491824 sendto(4, \"{\\\"seq\\\": 0, \\\"kelembapan\\\": 53.5, "
            "\\\"\"..., 46, 0, {sa_family=AF_INET, sin_port=htons(9999), "
            "sin_addr=inet_addr(\"127.0.0.1\")}, 16) = 46\n"
            "159889 18:10:55.649891 sendto(4, \"{\\\"seq\\\": 3, \\\"kelembapan\\\": 53.55, "
            "\\\"\"..., 47, 0, {sa_family=AF_INET, sin_port=htons(9999), "
            "sin_addr=inet_addr(\"127.0.0.1\")}, 16) = 47")
    par(d, "Nilai 12 pada hitungan fsync sama dengan jumlah rekaman yang ditulis, dan 4 pada "
           "sendto sama dengan jumlah rekaman yang dikirim (setiap rekaman ketiga). Kecocokan ini "
           "menunjukkan jejak strace memang mencerminkan program, bukan kumpulan kegiatan lain.")
    gambar(d, f"{BUKTI}/rapi-07-jaringan.png", 15.0,
           "Gambar 4.4 Pemanggilan openat, write, fsync, dan sendto pada jejak lengkap")

    h2(d, "4.5 Langkah 5: Mengelompokkan dan menghitung porsi")
    par(d, "klasifikasi.py membaca ringkasan strace lalu memetakan setiap system call ke "
           "keluarganya. Peta keluarga ditulis eksplisit di dalam skrip agar pengelompokan dapat "
           "diperiksa ulang dan hasilnya tidak bergantung pada tebakan.")
    kode(d, "$ python3 klasifikasi.py\n"
            "Keluarga      Syscall  Panggilan   Galat  Waktu (ms)   Porsi\n"
            "--------------------------------------------------------------\n"
            f"Proses              {len(k['per_keluarga']['Proses']['syscall']):>2}      "
            f"{k['per_keluarga']['Proses']['panggilan']:>6}     "
            f"{k['per_keluarga']['Proses']['galat']:>4}     "
            f"{k['per_keluarga']['Proses']['detik'] * 1000:>8.3f}   "
            f"{k['per_keluarga']['Proses']['panggilan'] / k['total_panggilan'] * 100:>6.1f}%\n"
            f"Berkas             {len(k['per_keluarga']['Berkas']['syscall']):>2}      "
            f"{k['per_keluarga']['Berkas']['panggilan']:>6}     "
            f"{k['per_keluarga']['Berkas']['galat']:>4}     "
            f"{k['per_keluarga']['Berkas']['detik'] * 1000:>8.3f}   "
            f"{k['per_keluarga']['Berkas']['panggilan'] / k['total_panggilan'] * 100:>6.1f}%\n"
            f"Jaringan           {len(k['per_keluarga']['Jaringan']['syscall']):>2}      "
            f"{k['per_keluarga']['Jaringan']['panggilan']:>6}     "
            f"{k['per_keluarga']['Jaringan']['galat']:>4}     "
            f"{k['per_keluarga']['Jaringan']['detik'] * 1000:>8.3f}   "
            f"{k['per_keluarga']['Jaringan']['panggilan'] / k['total_panggilan'] * 100:>6.1f}%\n"
            f"Memori             {len(k['per_keluarga']['Memori']['syscall']):>2}      "
            f"{k['per_keluarga']['Memori']['panggilan']:>6}     "
            f"{k['per_keluarga']['Memori']['galat']:>4}     "
            f"{k['per_keluarga']['Memori']['detik'] * 1000:>8.3f}   "
            f"{k['per_keluarga']['Memori']['panggilan'] / k['total_panggilan'] * 100:>6.1f}%\n"
            f"Lain-lain          {len(k['per_keluarga']['Lain-lain']['syscall']):>2}      "
            f"{k['per_keluarga']['Lain-lain']['panggilan']:>6}     "
            f"{k['per_keluarga']['Lain-lain']['galat']:>4}     "
            f"{k['per_keluarga']['Lain-lain']['detik'] * 1000:>8.3f}   "
            f"{k['per_keluarga']['Lain-lain']['panggilan'] / k['total_panggilan'] * 100:>6.1f}%\n"
            "--------------------------------------------------------------\n"
            f"TOTAL              {k['jumlah_syscall_unik']:>2}     {k['total_panggilan']:>7}"
            f"   {sum(v['galat'] for v in k['per_keluarga'].values()):>5}"
            f"   {k['total_detik'] * 1000:>8.3f}  100.0%")
    gambar(d, f"{BUKTI}/rapi-09-klasifikasi.png", 15.0,
           "Gambar 4.5 Hasil pengelompokan system call ke dalam lima keluarga")

    h2(d, "4.6 Langkah 6: Memeriksa struktur kernel")
    par(d, "Langkah terakhir mencatat sifat kernel yang menjalankan jejak di atas: versinya, "
           "jumlah nomor system call yang terdaftar, dan apakah modul dapat dimuat.")
    kode(d, "$ uname -r && grep -c \"^#define __NR_\" "
            "/usr/include/x86_64-linux-gnu/asm/unistd_64.h\n"
            f"{k['kernel']}\n"
            f"{k['jumlah_syscall']}\n\n"
            "$ lsmod | tail -n +2 | wc -l\n"
            f"{k['jumlah_modul']}")
    gambar(d, f"{BUKTI}/rapi-10-kernel.png", 15.0,
           "Gambar 4.6 Versi kernel, jumlah syscall terdaftar, dan jumlah modul aktif")


def hasil(d, k):
    h1(d, "5. Hasil dan Analisis")

    h2(d, "5.1 Hasil")
    par(d, "Tabel 5.1 menyajikan komposisi system call per keluarga. Seluruhnya ada "
           f"{k['jumlah_syscall_unik']} system call berbeda dengan {k['total_panggilan']} "
           "panggilan, dihitung dari satu kali eksekusi yang menulis "
           f"{k['rekaman_log']} rekaman sensor.")
    urut = ["Proses", "Berkas", "Jaringan", "Memori", "Lain-lain"]
    baris = []
    for i, nama in enumerate(urut, start=1):
        v = k["per_keluarga"].get(nama)
        if not v:
            continue
        teratas = ", ".join(s[0] for s in v["syscall"][:3])
        baris.append((i, nama, len(v["syscall"]), v["panggilan"], v["galat"],
                      f"{v['detik'] * 1000:.3f}",
                      f"{v['panggilan'] / k['total_panggilan'] * 100:.1f}%", teratas))
    tabel(d, ["No", "Keluarga", "Syscall", "Panggilan", "Galat", "Waktu (ms)", "Porsi",
              "Tiga teratas"], baris,
          lebar=[0.9, 2.0, 1.5, 1.9, 1.3, 1.9, 1.5, 5.3], ukuran=8)
    caption(d, "Tabel 5.1 Komposisi system call per keluarga pada sensor_log.py")

    par(d, "Tabel 5.2 memuat rincian system call yang punya kaitan langsung dengan pekerjaan "
           "program, yaitu menulis ke berkas, memaksa sinkronisasi, dan mengirim data.")
    tabel(d, ["System call", "Keluarga", "Jumlah", "Makna pada program ini"], [
        ("openat", "Berkas", "65",
         "Membuka results/sensor.log dengan O_CREAT|O_TRUNC; sisanya pembukaan pustaka"),
        ("write", "Berkas", "13",
         "Menulis baris JSON ke berkas log; 12 rekaman ditambah satu penutup"),
        ("fsync", "Berkas", "12", "Memaksa data rekaman turun ke media penyimpanan"),
        ("close", "Berkas", "65", "Menutup berkas dan pustaka yang sudah dibuka"),
        ("newfstatat", "Berkas", "218",
         "Memeriksa keberadaan berkas modul Python; 62 di antaranya gagal"),
        ("sendto", "Jaringan", "4", "Mengirim rekaman ke gateway 127.0.0.1:9999"),
        ("socket", "Jaringan", "4", "Membuat soket UDP per pengiriman"),
        ("clock_nanosleep", "Lain-lain", "12", "Tidur 50 ms antar rekaman"),
        ("execve", "Proses", "1", "Memuat program python3 beserta argumennya"),
        ("mmap", "Memori", "32", "Memetakan pustaka bersama dan area anonim"),
        ("brk", "Memori", "16", "Menaikkan batas heap untuk objek Python"),
    ], lebar=[3.4, 2.2, 1.8, 7.8], ukuran=8.5)
    caption(d, "Tabel 5.2 System call yang berkaitan langsung dengan pekerjaan program")

    par(d, "Gambar 5.1 memperlihatkan porsi tiap keluarga terhadap keseluruhan panggilan.")
    gambar(d, "results/gambar-komposisi.png", 14.5,
           "Gambar 5.1 Porsi system call per keluarga")

    par(d, "Gambar 5.2 memperlihatkan di mana waktu kernel sebenarnya dihabiskan, dan Gambar 5.3 "
           "menampilkan system call yang paling sering dipanggil.")
    gambar(d, "results/gambar-waktu-kernel.png", 13.5,
           "Gambar 5.2 Waktu yang dihabiskan di kernel per keluarga")
    gambar(d, "results/gambar-syscall-teratas.png", 14.5,
           "Gambar 5.3 Sepuluh system call paling sering dipanggil")

    h2(d, "5.2 Analisis")
    par(d, "Poin (1) deskripsi tugas — pengelompokan system call. Dari 39 system call yang "
           "muncul, 82,0 persen panggilan masuk keluarga berkas. Angka itu lebih besar dari "
           "perkiraan awal, dan penyebabnya bukan pekerjaan program. Program hanya melakukan 12 "
           "penulisan ke berkas log dan 12 fsync, tetapi ada 218 panggilan newfstatat dan 81 "
           "panggilan read yang sebagian besar berasal dari proses memuat modul Python. Python "
           "mencari setiap modul dengan mencoba banyak kemungkinan lokasi, dan setiap percobaan "
           "menghasilkan satu openat atau newfstatat — 62 di antaranya berakhir dengan galat "
           "karena berkasnya memang tidak ada. Jadi keluarga berkas mendominasi karena biaya "
           "impor pustaka, bukan karena programnya banyak menulis.")
    par(d, "Keluarga memori menempati urutan kedua dengan 6,6 persen. Isinya didominasi mmap "
           "sebanyak 32 panggilan, yang sebagian besar dipakai memetakan pustaka bersama seperti "
           "libm.so.6 dan libz.so.1 ke ruang alamat proses. brk hanya dipanggil 16 kali untuk "
           "menaikkan batas heap, karena sebagian besar objek Python dialokasikan dari arena "
           "yang sudah dipetakan lewat mmap. Keluarga proses tercatat 8,3 persen, dan yang "
           "paling menonjol justru rt_sigaction sebanyak 66 kali — itu pemasangan penangan "
           "sinyal oleh Python saat mulai berjalan, bukan pembuatan proses. clone dan execve "
           "masing-masing hanya sekali.")
    par(d, "Keluarga jaringan mencatat angka terkecil, 0,9 persen, dengan 4 soket dan 4 sendto. "
           "Itu sesuai rancangan program: hanya setiap rekaman ketiga yang dikirim. Kalau gateway "
           "lokal tidak mendengarkan, sendto tetap berhasil karena UDP tidak memerlukan sambungan, "
           "dan program tidak terhenti. Sifat ini penting untuk sistem lapangan: kegagalan "
           "jaringan tidak boleh menghentikan pencatatan data.")
    par(d, "Poin (2) deskripsi tugas — peralihan user mode ke kernel mode. Jejak pada Gambar 4.4 "
           "memperlihatkan urutan yang jelas. Baris openat tercatat pada 18:10:55.489365, "
           "disusul write pertama pada 18:10:55.489676 — selisih 311 mikrodetik. Di antara kedua "
           "baris itu program masih berjalan di user mode: menyusun objek Python, mengubahnya "
           "menjadi JSON, dan mengubahnya lagi menjadi byte. strace tidak mencatat apa pun pada "
           "selang itu, karena strace hanya melihat saat kendali menyeberang ke kernel.")
    par(d, "Setiap baris yang tercatat adalah satu peralihan penuh user ke kernel dan kembali. "
           "Pada write(3, ...) = 46, prosesor menyimpan status, berpindah ke stack kernel, "
           "mengambil nomor system call dari %rax, memanggil penangan untuk write, menyalin 46 "
           "byte dari ruang pengguna ke page cache, lalu kembali ke user mode dengan nilai 46 "
           "pada register hasil. Waktu yang dihabiskan di kernel untuk seluruh 890 panggilan "
           f"hanya {k['total_detik'] * 1000:.3f} milidetik, sementara program berjalan lebih dari "
           "satu detik. Artinya lebih dari 99 persen waktu program dihabiskan di user mode, "
           "sebagian besar justru di dalam clock_nanosleep yang sengaja menunggu.")
    par(d, "Baris fsync memperlihatkan peralihan yang lebih mahal. fsync bukan sekadar menyalin "
           "ke page cache seperti write; ia meminta kernel menunggu sampai data benar-benar "
           "tertulis ke media penyimpanan. Dengan 12 panggilan fsync untuk 12 rekaman, program "
           "memaksa satu perjalanan ke disk per rekaman. Pada beban nyata dengan pembacaan tiap "
           "lima detik itu masih wajar, tetapi bila jeda dipersingkat menjadi 0,1 detik, "
           "kebijakan ini akan menjadi hambatan utama.")
    par(d, "Poin (3) deskripsi tugas — kaitan dengan struktur kernel. Mesin ini menjalankan "
           f"kernel {k['kernel']} dengan arsitektur monolitik: {k['jumlah_syscall']} nomor system "
           "call terdaftar pada header, dan seluruh penangan untuk nomor-nomor itu berada dalam "
           "satu ruang alamat kernel. Karena itu perpindahan dari subsistem berkas ke subsistem "
           "memori saat write menyalin data tidak memerlukan peralihan mode lagi. Inilah sebabnya "
           "waktu kernel per panggilan hanya berkisar beberapa mikrodetik, sebagaimana terlihat "
           "pada kolom usecs/call yang nilainya 1 sampai 33 mikrodetik.")
    par(d, f"Kernel yang sama juga memuat {k['jumlah_modul']} modul aktif. Keberadaan modul "
           "menunjukkan bahwa meski monolitik, Linux tidak menuntut seluruh pengandar perangkat "
           "masuk ke kernel inti. Modul jaringan seperti tcp_diag dan inet_diag dimuat saat "
           "dibutuhkan dan bisa dilepas lagi. Pada jejak strace, hal ini tidak terlihat langsung "
           "sebagai system call, karena pemuatan modul diurus kernel sendiri saat panggilan "
           "socket pertama kali terjadi. Bagi pengamat strace, efeknya hanya berupa panggilan "
           "socket pertama yang terasa sedikit lebih lambat.")
    par(d, "Satu hal yang perlu dicatat jujur: strace sendiri mengubah perilaku program. Setiap "
           "system call yang dilacak memerlukan pemberitahuan ke proses pelacak dan penghentian "
           "sementara. Program yang normalnya selesai dalam hitungan mikrodetik bisa menjadi "
           "beberapa kali lebih lambat di bawah strace. Karena itu angka pada Tabel 5.1 lebih "
           "tepat dibaca sebagai komposisi dan proporsi, bukan sebagai patokan kecepatan "
           "sebenarnya. Proporsi antar keluarga tetap sahih, karena beban pelacakan mengenai "
           "semua panggilan dengan cara yang sama.")

    h2(d, "5.3 Catatan keterbatasan")
    par(d, "Program yang ditelusuri adalah simulasi. Nilai sensor dibangkitkan, gateway lokal "
           "tidak benar-benar menerima data, dan berkas log ditulis ke penyimpanan mesin "
           "operator, bukan ke kartu microSD gateway. Jumlah system call pada perangkat keras "
           "sesungguhnya akan berbeda karena pustaka dan pengandar perangkatnya berbeda. "
           "Perbandingan pada laporan ini berlaku untuk program yang sama dijalankan pada mesin "
           "yang sama, bukan sebagai patokan umum.")


def kesimpulan(d, k):
    h1(d, "6. Kesimpulan")
    par(d, f"Penelusuran dengan strace menghasilkan {k['jumlah_syscall_unik']} system call "
           f"berbeda dan {k['total_panggilan']} panggilan dari satu eksekusi yang menulis "
           f"{k['rekaman_log']} rekaman sensor. Keluarga berkas mendominasi dengan 82,0 persen, "
           "tetapi penyebabnya adalah proses memuat modul Python, bukan penulisan data sensor; "
           "hanya 12 write dan 12 fsync yang benar-benar menulis rekaman. Peralihan user ke "
           "kernel terjadi sekali untuk setiap baris yang tercatat, dan seluruhnya hanya memakan "
           f"{k['total_detik'] * 1000:.3f} milidetik, jauh di bawah waktu yang dihabiskan program "
           "di user mode. Kernel monolitik Linux dengan modul yang dapat dimuat menjelaskan "
           "mengapa biaya per panggilan sangat kecil dan mengapa pemuatan modul jaringan tidak "
           "terlihat sebagai system call tersendiri.")


def kepingan(d):
    h1(d, "7. Kepingan Puzzle")
    tabel(d, ["Keterangan", "Isi"], [
        ("Nomor kepingan", "#2"),
        ("Isi kepingan", "Jejak strace program sensor, tabel klasifikasi system call ke lima "
                         "keluarga, grafik komposisi dan waktu kernel, serta analisis peralihan "
                         "mode"),
        ("Lokasi di portofolio", REPO),
        ("Dipakai untuk", "Level 1 Puzzle UTS — menyambung kepingan #1 (peta ekosistem) karena "
                          "simpul yang dipetakan di sana menentukan jenis system call yang "
                          "diamati di sini, dan menjadi dasar kepingan #3 (proses dan thread) "
                          "yang memakai clone dan execve dari jejak ini"),
    ], lebar=[4.2, 11.0])


def pustaka(d):
    h1(d, "Daftar Pustaka")
    for teks in [
        "Kerrisk, M. (2010). The Linux programming interface. No Starch Press.",
        "Love, R. (2010). Linux kernel development (3rd ed.). Addison-Wesley.",
        "Silberschatz, A., Galvin, P. B., & Gagne, G. (2018). Operating system concepts "
        "(10th ed.). Wiley.",
        "The strace project. (2024). strace: Trace system calls and signals (Version 6.8) "
        "[Perangkat lunak]. https://strace.io",
    ]:
        p = d.add_paragraph(style="Normal")
        p.paragraph_format.left_indent = Cm(1.0)
        p.paragraph_format.first_line_indent = Cm(-1.0)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.add_run(teks)


def lampiran(d):
    d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    h1(d, "Lampiran A. Kode Program dan Log")
    par(d, "Empat berkas di bawah ini menghasilkan seluruh angka pada laporan. Keluaran strace "
           "lengkap tidak disertakan karena panjangnya 885 baris; berkasnya tersedia pada "
           "repositori portofolio.")
    for nama in ("sensor_log.py", "klasifikasi.py", "figures.py", "ambil-bukti.sh"):
        p = d.add_paragraph(style="Normal")
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run(f"A.{nama}")
        r.bold = True
        r.font.size = Pt(9.5)
        kode(d, baca_berkas(nama), ukuran=7)

    h1(d, "Lampiran B. Pernyataan Penggunaan AI Generatif")
    par(d, "☐  Saya tidak menggunakan AI generatif dalam tugas ini.")
    par(d, "☒  Menggunakan AI generatif dengan rincian berikut:")
    tabel(d, ["Alat", "Tujuan penggunaan", "Bagian yang dibantu", "Cara memverifikasi"], [
        ("Claude (Anthropic)", "Menyusun skrip pengelompokan dan merapikan kalimat laporan",
         "Bagian 4 (kode), Bagian 5.2",
         "Seluruh angka berasal dari keluaran strace pada tangkapan layar; klasifikasi.py "
         "dijalankan ulang dan hasilnya dicocokkan dengan ringkasan strace"),
    ], lebar=[3.0, 4.4, 4.0, 4.4], ukuran=8.5)

    h1(d, "Lampiran C. Daftar Periksa Sebelum Mengumpulkan")
    for teks, sudah in [
        ("Semua teks petunjuk abu-abu dan kotak petunjuk sudah dihapus.", True),
        ("Identitas, kode tugas, dan nama host pada sampul sudah benar.", True),
        ("Setiap poin deskripsi tugas sudah dijawab di bagian Analisis.", True),
        ("Setiap tangkapan layar menampilkan prompt dan memiliki nomor serta keterangan.", True),
        ("Kepingan puzzle sudah disimpan di portofolio dan tautannya dicantumkan.", True),
        ("Pernyataan penggunaan AI generatif sudah diisi.", True),
        ("Berkas disimpan sebagai PDF dengan nama C_I-2_<NIM>_<Nama>.pdf.", True),
    ]:
        p = d.add_paragraph(style="Normal")
        p.paragraph_format.space_after = Pt(3)
        p.add_run(f"{'☒' if sudah else '☐'}  {teks}")

    par(d, "")
    h2(d, "Swa-nilai berdasarkan kriteria lembar tugas")
    tabel(d, ["Kriteria (dari lembar tugas)", "Bobot", "Sudah terpenuhi? Di bagian mana"],
          [("Ketepatan konsep", "35%",
            "Ya — pengelompokan lima keluarga dan penjelasan peralihan mode di Bagian 5.2"),
           ("Kedalaman analisis", "30%",
            "Ya — dominasi berkas dijelaskan dari impor modul, biaya fsync dibahas terpisah"),
           ("Bukti praktik/perhitungan", "25%",
            "Ya — 10 tangkapan layar strace asli dan tabel dengan angka terukur"),
           ("Orisinalitas dan kerapian", "10%",
            "Ya — grafik dibuat dari data rekaman, daftar pustaka memakai gaya APA")],
          lebar=[5.2, 2.0, 8.0])


def main():
    d = docx.Document(TEMPLATE)
    bersihkan(d)

    k = baca_klasifikasi()
    k["rekaman_log"] = k.get("rekaman_log", 12)
    k.update(fakta_kernel())

    sampul_i2(d)
    pendahuluan(d, k)
    dasar_teori(d, k)
    lingkungan(d, k)
    langkah(d, k)
    hasil(d, k)
    kesimpulan(d, k)
    kepingan(d)
    pustaka(d)
    lampiran(d)

    header_dokumen(d, "Laporan Tugas Individu Sistem Operasi · ", f"{KELAS} · {KODE}")
    nomor_halaman(d)

    d.core_properties.title = "I-2 Penelusuran System Call dan Struktur Kernel"
    d.core_properties.author = NAMA
    d.core_properties.subject = "Sistem Operasi (USA-WP2260110), IF-3C"
    d.core_properties.last_modified_by = NAMA

    os.makedirs("results", exist_ok=True)
    d.save(OUT)
    print("tersimpan:", OUT)


if __name__ == "__main__":
    main()
