---
name: fire-detector-dev
description: Panduan dan workflow pengembangan, pengujian, dan penambahan fitur pada proyek Fire-Detector-Lite (FlameVision AI). Gunakan skill ini ketika hendak memodifikasi algoritma deteksi, menambah endpoint web, atau memperluas antarmuka GUI.
---

# Fire Detector Development Skill

Skill ini membantu agent dan developer dalam memelihara dan mengembangkan proyek **Fire-Detector-Lite (FlameVision AI)**.

## 1. Quick Reference File Map

- **Logika Inti Deteksi**: `src/detector.py` (`FireDetector.detect()`, `FireDetector.update_params()`)
- **Visualisasi & Rendering HUD**: `src/utils.py` (`draw_fire_boxes()`, `create_side_by_side_view()`, `play_alarm_sound()`)
- **Desktop OpenCV GUI**: `src/app.py` (`DesktopFireApp.run()`)
- **Web App Backend**: `web_app.py` (Flask server, `/process_frame`, `/calibrate`, `/status`)
- **Web App Frontend**: `templates/index.html`, `static/style.css`
- **Unit Testing**: `tests/test_detector.py`

## 2. Standar Alur Deteksi (Detection Pipeline)

1. **Pre-processing**: Frame di-resize jika perlu, diaplikasikan `cv2.GaussianBlur(frame, (15, 15), 0)`.
2. **Color Filtering**:
   - `cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)` -> `cv2.inRange(hsv, lower_hsv, upper_hsv)`
   - Filter tambahan pada kanal BGR & YCrCb untuk verifikasi luminansi api.
3. **Morfologi**: `cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)` diikuti `cv2.dilate()`.
4. **Kontur & Evaluasi**: `cv2.findContours()` -> Filter kontur `area >= min_contour_area` -> Hitung *bounding box* & *confidence*.

## 3. Menjalankan & Menguji Kode

```bash
# Menjalankan unit test
python -m unittest discover tests

# Menguji detektor pada video sampel
python main.py --source sample_fire.mp4

# Menjalankan server web dashboard
python web_app.py --port 5000
```
