# Fire-Detector-Lite (FlameVision AI)

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/OpenCV-4.x-green.svg)](https://opencv.org/)
[![Web Framework](https://img.shields.io/badge/Flask-3.x-red.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)](LICENSE)

> **Sistem Deteksi Api Real-Time Berbasis Computer Vision & Web Dashboard**  
> Pengembang: **Diva Aurel Anastacia Sirait**

---

## 📌 Ringkasan Proyek

**FlameVision AI** adalah sistem deteksi api (*fire detection*) berbasis *Computer Vision* yang beroperasi secara *real-time* tanpa memerlukan akselerasi perangkat keras khusus/GPU. Sistem ini memproses aliran video dari webcam laptop/PC, kamera smartphone (via HTML5 WebRTC di browser), maupun berkas video rekaman.

Sistem mendeteksi api menggunakan segmentasi ruang warna ganda (**HSV & YCrCb/RGB Rule-Based**), pembersihan noise dengan morfologi citra (*opening & dilation*), dan analisis kontur (*contour analysis*) untuk menentukan koordinat *bounding box* dan tingkat keyakinan (*confidence level*).

---

## ✨ Fitur Utama

- 🎯 **Real-time Fire Detection**: Deteksi api presisi tinggi dengan *bounding box* dan HUD status peringatan.
- 📱 **Web Dashboard & Cross-Platform WebRTC**: Akses kamera depan/belakang smartphone secara langsung melalui browser di jaringan Wi-Fi lokal.
- 🖥️ **Desktop GUI (OpenCV)**: Antarmuka jendela bawaan lengkap dengan slider kalibrasi interaktif (*trackbars*).
- 🚨 **Multi-Channel Alert System**: Banner status visual, audio sirene alarm berbasis Web Audio API di browser, serta alarm native Windows (`winsound`).
- 🔄 **Multi-View Inspection**: Mode tampilan *Annotated*, *Split-Screen Debug*, *Inferno/Fire Mask*, dan *Raw Stream*.
- 📸 **Snapshot Capture & Gallery**: Penyimpanan bukti tangkapan layar otomatis saat api terdeteksi maupun secara manual.
- 🧪 **Simulation Ready**: Disertai video simulasi kobaran api (`sample_fire.mp4`) dan skrip pembuat video sintetis (`generate_test_video.py`).

---

## 📁 Struktur Direktori

```text
├── .agents/
│   └── rules/
│       └── project_guidelines.md # Panduan arsitektur dan konvensi pengembangan
├── src/
│   ├── __init__.py               # Inisialisasi modul src
│   ├── detector.py               # Algoritma pendeteksi api (Dual Color-Space + Morph)
│   ├── utils.py                  # Rendering HUD, bounding box, dan audio alarm
│   └── app.py                    # Aplikasi desktop OpenCV GUI & trackbars
├── templates/
│   └── index.html                # Tampilan Web Dashboard & WebRTC Client
├── static/
│   └── style.css                 # Desain antarmuka modern glassmorphism & responsif
├── tests/
│   ├── __init__.py               # Inisialisasi modul pengujian
│   └── test_detector.py          # Unit test otomatis untuk detektor api
├── snapshots/                    # Direktori penyimpanan snapshot hasil deteksi
├── main.py                       # Titik masuk aplikasi desktop GUI
├── web_app.py                    # Server Web Dashboard berbasis Flask
├── generate_test_video.py        # Generator video sintetis api untuk pengujian
├── sample_fire.mp4               # Berkas video sampel api
├── run.bat                       # Launcher 1-klik untuk Aplikasi Desktop
├── run_web.bat                   # Launcher 1-klik untuk Web Dashboard Flask
├── requirements.txt              # Daftar dependensi Python
├── docs/
│   ├── PROJECT_DESCRIPTION.md   # Ringkasan singkat proyek
│   └── PROJECT_DOCUMENTATION.md # Dokumentasi teknis lengkap dan arsitektur
└── README.md                     # Panduan komprehensif repositori
```

---

## 🚀 Panduan Instalasi & Penggunaan

### 1. Prasyarat
- Python 3.8 atau versi lebih baru
- Virtual environment (direkomendasikan)

### 2. Instalasi Dependensi
```bash
# Clone repositori atau buka folder proyek
git clone https://github.com/divaarlfs/Fire-Detector-Lite.git
cd Fire-Detector-Lite

# Instal paket dependensi
pip install -r requirements.txt
```

### 3. Menjalankan Web Dashboard
```bash
# Menggunakan batch file:
run_web.bat

# Atau via terminal:
python web_app.py --port 5000
```
- Akses di PC/Laptop: `http://localhost:5000`
- Akses dari HP (jaringan Wi-Fi sama): `http://<IP-Lokal-Komputer>:5000`

### 4. Menjalankan Aplikasi Desktop (OpenCV Native)
```bash
# Menggunakan batch file:
run.bat

# Menggunakan webcam bawaan:
python main.py

# Menggunakan file simulasi video:
python main.py --source sample_fire.mp4
```

### 5. Menjalankan Unit Test
```bash
python -m unittest discover tests
```

---

## ⚙️ Parameter Deteksi (HSV & Morfologi)

| Parameter | Default | Keterangan |
| :--- | :--- | :--- |
| `H_min`, `H_max` | `0` - `25` | Spektrum rona merah hingga kuning kobaran api |
| `S_min`, `S_max` | `100` - `255` | Saturasi intensitas warna api |
| `V_min`, `V_max` | `190` - `255` | Tingkat kecerahan/luminansi api |
| `min_contour_area` | `600` | Luas area minimum kontur (piksel) untuk mencegah deteksi noise |
| `morph_kernel_size`| `5` | Ukuran matriks kernel operasi morfologi |

---

## 📜 Lisensi

Proyek ini dikembangkan oleh **Diva Aurel Anastacia Sirait** dan dirilis di bawah lisensi [MIT License](LICENSE).