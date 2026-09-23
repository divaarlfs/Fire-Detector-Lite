# Antigravity Agent Guidelines for Fire-Detector-Lite (FlameVision AI)

Dokumen ini berisi konteks arsitektur, standar kode, dan petunjuk teknis agar AI Agent (Antigravity) dapat memahami, memelihara, dan mengembangkan proyek ini di masa mendatang secara konsisten.

---

## 📌 Ringkasan Sistem & Arsitektur

- **Nama Proyek:** FlameVision AI (Fire-Detector-Lite)
- **Author/Developer:** Diva Aurel Anastacia Sirait
- **Domain:** Real-Time Computer Vision & Image Processing
- **Stack Utama:** Python (>=3.8), OpenCV (`cv2`), NumPy, Flask, HTML5/CSS3 (Vanilla Glassmorphism), WebRTC (`getUserMedia`), Web Audio API.

### Komponen Inti:
1. `src/detector.py`: Kelas `FireDetector` yang mengimplementasikan segmentasi ruang warna ganda:
   - **HSV Filter**: `H: [0, 25]`, `S: [100, 255]`, `V: [190, 255]`.
   - **RGB/YCrCb Rule Filter**: $R > G > B$, $R > 150$, $Cr > Cb + 10$, $Y > 100$.
   - **Operasi Morfologi**: Gaussian Blur ($k=15$), Morphological Opening & Dilation ($k=5$).
   - **Analisis Kontur**: `cv2.findContours`, filter area $\ge 600\text{ px}$, kalkulasi *pixel density* untuk *confidence score*.
2. `src/utils.py`: Fungsi pembantu rendering anotasi (`draw_fire_boxes`), split screen (`create_side_by_side_view`), color mapping inferno, dan alarm audio non-blocking (`winsound`).
3. `src/app.py`: Aplikasi GUI desktop OpenCV native dengan trackbar kalibrasi langsung.
4. `web_app.py`: Server Flask web streaming + REST API (`/status`, `/process_frame`, `/calibrate`, `/api/snapshots`, `/capture_snapshot`).
5. `templates/index.html` & `static/style.css`: Antarmuka web modern dengan dukungan stream kamera lokal/WebRTC, switch mode tampilan, kontrol kalibrasi interaktif, dan visual siren.
6. `tests/test_detector.py`: Pengujian otomatis unit test deteksi sintetis, blank frame, dan dynamic parameters.

---

## 🛠️ Konvensi Pengembangan & Aturan Modifikasi

1. **Efisiensi Algoritma (No Heavyweight ML / GPU requirements)**:
   - Jangan menambahkan model deep learning berat (seperti YOLO besar atau PyTorch/TensorFlow berat) kecuali diminta secara eksplisit oleh pengguna, karena sistem ini dirancang ringan (*lite*), cepat, dan dapat berjalan di CPU dengan latensi rendah.
2. **Kesesuaian Antarmuka Web & Desktop**:
   - Jika menambahkan parameter baru pada `FireDetector`, pastikan parameter tersebut diekspos di:
     1. OpenCV Trackbar di [app.py](file:///c:/Users/divaa/OneDrive/Desktop/Antigravity%20Project%20Full%20Set/Antigravity%20IDE%20Project%202/src/app.py)
     2. Endpoint `/calibrate` dan panel kontrol di [web_app.py](file:///c:/Users/divaa/OneDrive/Desktop/Antigravity%20Project%20Full%20Set/Antigravity%20IDE%20Project%202/web_app.py) & [templates/index.html](file:///c:/Users/divaa/OneDrive/Desktop/Antigravity%20Project%20Full%20Set/Antigravity%20IDE%20Project%202/templates/index.html).
3. **Threading & Non-Blocking**:
   - Audio dan pemrosesan stream tidak boleh memblokir thread utama Flask atau GUI OpenCV. Gunakan thread terpisah atau Web Audio API di sisi klien browser.
4. **Unit Testing**:
   - Setiap perubahan pada logika deteksi harus tetap lolos pengujian pada `tests/test_detector.py`. Jalankan `python -m unittest discover tests` untuk memverifikasi.
5. **Styling & UI**:
   - Gunakan Vanilla CSS dengan desain modern, dark theme, glassmorphism, dan transisi halus tanpa dependensi pustaka CSS eksternal yang berat.
