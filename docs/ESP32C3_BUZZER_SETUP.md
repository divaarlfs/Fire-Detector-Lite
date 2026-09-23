# Panduan Integrasi ESP32-C3 Mini Buzzer MQTT (FlameVision AI)

Panduan ini menjelaskan cara menghubungkan modul mikrofon/mikrokontroler **ESP32-C3 SuperMini** ke buzzer dan mengintegrasikannya dengan sistem deteksi api **FlameVision AI** melalui protokol MQTT.

---

## 1. Skema Pengkabelan (Wiring Diagram)

| Pin ESP32-C3 SuperMini | Pin Komponen Buzzer | Keterangan |
| :--- | :--- | :--- |
| **3V3 / 5V** | VCC / (+) Buzzer | Sumber daya (3.3V atau 5V sesuai modul buzzer) |
| **GND** | GND / (-) Buzzer | Ground bersama |
| **GPIO 5** | I/O / S (Signal) Buzzer | Pin kendali sinyal PWM nada militer |
| **GPIO 8** | Onboard LED | Indikator status (Built-in pada ESP32-C3) |

> **Catatan:** Anda bisa menggunakan **Passive Buzzer** (untuk menghasilkan nada sirene militer naik-turun frekuensi) maupun **Active Buzzer**.

---

## 2. Persiapan Arduino IDE

1. Buka **Arduino IDE** (versi 2.x disarankan).
2. Pasang board ESP32 di **Boards Manager**:
   - Cari `esp32` by *Espressif Systems* lalu klik **Install**.
3. Pilih board: **Tools > Board > ESP32C3 Dev Module** (atau *ESP32-C3 SuperMini*).
4. Pasang library MQTT:
   - Buka **Sketch > Include Library > Manage Libraries...**
   - Cari dan pasang: `PubSubClient` by *Nick O'Leary*.

---

## 3. Unggah Firmware ke ESP32-C3

1. Buka file firmware proyek:
   [`firmware/esp32c3_buzzer/esp32c3_buzzer.ino`](file:///c:/Users/divaa/OneDrive/Desktop/Antigravity%20Project%20Full%20Set/Antigravity%20IDE%20Project%202/firmware/esp32c3_buzzer/esp32c3_buzzer.ino)
2. Sesuaikan nama dan password WiFi Anda:
   ```cpp
   const char* WIFI_SSID     = "NAMA_WIFI_ANDA";
   const char* WIFI_PASSWORD = "PASSWORD_WIFI_ANDA";
   ```
3. Pastikan broker dan topik MQTT sama dengan di dashboard web FlameVision:
   ```cpp
   const char* MQTT_BROKER   = "76.13.19.250";
   const int   MQTT_PORT     = 1883;
   const char* MQTT_TOPIC    = "flamevision/fire_alert";
   ```
4. Hubungkan kabel USB ESP32-C3 ke komputer, pilih Port COM yang sesuai, lalu klik tombol **Upload**.

---

## 4. Format Payload MQTT

Saat api terdeteksi, server FlameVision AI secara otomatis mempublikasikan pesan JSON ke topik `flamevision/fire_alert`:

### A. Kondisi Api Terdeteksi (DARURAT):
```json
{
  "alert": true,
  "status": "FIRE_DETECTED",
  "command": "ALARM_MILITARY_ON",
  "count": 2,
  "confidence": 96.5,
  "timestamp": 1727083200
}
```

### B. Kondisi Api Padam / Aman (PULIH):
```json
{
  "alert": false,
  "status": "SAFE",
  "command": "ALARM_OFF",
  "count": 0,
  "confidence": 0.0,
  "timestamp": 1727083230
}
```

---

## 5. Pengujian Melalui Dashboard Web

1. Buka dashboard web FlameVision: `http://127.0.0.1:5000`
2. Pada panel samping kanan, perhatikan kartu **ESP32-C3 MQTT Buzzer**.
3. Klik tombol **"▶ Tes Buzzer"** untuk mengirim sinyal uji coba langsung ke ESP32-C3.
4. Buzzer pada ESP32-C3 akan langsung berbunyi dengan nada sirene militer (*Tactical Klaxon*).
