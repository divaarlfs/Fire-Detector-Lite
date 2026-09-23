/*
  =============================================================================
  🔥 Flame Vision - ESP32-C3 Loud Emergency Fire Alarm (Latch Mode)
  =============================================================================
  Board       : ESP32-C3 (SuperMini / NodeMCU)
  Pin Buzzer  : GPIO 5
  Pin LED     : GPIO 8 (Onboard)
  Pin Tombol  : GPIO 9 (Tombol BOOT Onboard ESP32-C3)
  Broker      : 76.13.19.250:1883
  Topic       : flamevision/fire_alert
  
  FITUR KEAMANAN TINGGI (LATCH MODE):
  - Saat ada api terdeteksi (meskipun hanya 1 detik atau percikan singkat),
    alarm akan TERKUNCI (LATCHED) dan berbunyi TERUS MENERUS non-stop.
  - Alarm TIDAK AKAN MATI otomatis meskipun api sudah hilang dari kamera.
  - Alarm HANYA BISA DIMATIKAN ketika tombol BOOT fisik pada ESP32 ditekan!
  =============================================================================
*/

#include <WiFi.h>
#include <PubSubClient.h>

// ==================== 1. KONFIGURASI WIFI ====================
// ⚠️ GANTI DENGAN NAMA & PASSWORD WIFI / HOTSPOT ANDA:
const char* WIFI_SSID     = "NAMA_WIFI_ANDA";         // <-- Masukkan nama WiFi/Hotspot
const char* WIFI_PASSWORD = "PASSWORD_WIFI_ANDA";     // <-- Masukkan password WiFi

// ==================== 2. KONFIGURASI MQTT BROKER ====================
const char* MQTT_BROKER   = "76.13.19.250";
const int   MQTT_PORT     = 1883;
const char* MQTT_TOPIC    = "flamevision/fire_alert";
const char* CLIENT_ID     = "ESP32C3_FlameVision_Buzzer";

// ==================== 3. PENGATURAN PIN & TIPE BUZZER ====================
#define BUZZER_PIN        5     // Pin sinyal Buzzer (I/O atau SIG atau S)
#define LED_PIN           8     // LED onboard ESP32-C3 (aktif LOW)
#define BOOT_BUTTON_PIN   9     // Tombol BOOT onboard ESP32-C3 (aktif LOW)

/*
  PILIHAN TIPE BUZZER:
  1 = ACTIVE BUZZER (Tipe Active-HIGH / Standar) -> Kirim tegangan HIGH untuk bunyi
  2 = ACTIVE BUZZER (Tipe Active-LOW / Modul 3-Pin) -> Kirim sinyal LOW untuk bunyi
  3 = PASSIVE BUZZER (Speaker Piezo / Perlu Frekuensi AC tone)
*/
#define BUZZER_TYPE       1     // Diatur ke tipe 1 (Active-HIGH) agar mati saat kondisi aman

#define PASSIVE_FREQ_HZ   2800  // Frekuensi jika pakai tipe 3 (2800 Hz)
#define TEST_DURATION_MS  3500  // Durasi tombol uji dari web (3.5 detik)

// ==================== 4. STATE & OBJEK ====================
WiFiClient espClient;
PubSubClient mqttClient(espClient);

bool isAlarmLatched = false;        // Status alarm terkunci menyala
unsigned long silenceUntil = 0;     // Masa jeda hening setelah tombol BOOT ditekan
unsigned long testAlarmUntil = 0;
unsigned long lastWifiRetry = 0;
unsigned long lastMqttRetry = 0;
unsigned long lastBtnPressTime = 0;

// ==================== 5. FUNGSI DRIVER SUARA ====================
void buzzerON() {
  // Jangan membunyikan buzzer jika sedang dalam masa hening (Mute Cooldown)
  if (millis() < silenceUntil) {
    digitalWrite(LED_PIN, HIGH);
    return;
  }

  digitalWrite(LED_PIN, LOW); // Nyalakan LED Onboard

#if BUZZER_TYPE == 1
  // Active High
  digitalWrite(BUZZER_PIN, HIGH);
#elif BUZZER_TYPE == 2
  // Active Low (Paling umum untuk modul 3-pin dengan transistor PNP)
  digitalWrite(BUZZER_PIN, LOW);
#elif BUZZER_TYPE == 3
  // Passive Buzzer
  tone(BUZZER_PIN, PASSIVE_FREQ_HZ);
#endif
}

void buzzerOFF() {
  digitalWrite(LED_PIN, HIGH); // Matikan LED Onboard

#if BUZZER_TYPE == 1
  digitalWrite(BUZZER_PIN, LOW);
#elif BUZZER_TYPE == 2
  digitalWrite(BUZZER_PIN, HIGH);
#elif BUZZER_TYPE == 3
  noTone(BUZZER_PIN);
  digitalWrite(BUZZER_PIN, LOW);
#endif
}

// ==================== 6. PENERIMA PESAN MQTT ====================
void onMqttMessage(char* topic, byte* payload, unsigned int length) {
  String message = "";
  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }

  Serial.print("\n[MQTT DITERIMA] -> ");
  Serial.println(message);

  // Perintah Uji Buzzer dari Web Dashboard
  if (message.indexOf("TEST_BUZZER") >= 0 || message.indexOf("TEST_TRIGGER") >= 0) {
    Serial.println("[ALARM] >>> Uji Suara Buzzer (3.5 Detik)...");
    silenceUntil = 0; // Reset masa hening saat tes manual
    testAlarmUntil = millis() + TEST_DURATION_MS;
    buzzerON();
    return;
  }

  // Sinyal Bahaya Api Nyata -> Kunci Alarm (LATCH ON)
  if (message.indexOf("\"alert\":true") >= 0 || 
      message.indexOf("ALARM_MILITARY_ON") >= 0 || 
      message.indexOf("FIRE_DETECTED") >= 0) {
    
    // Jika masih dalam masa hening setelah tombol BOOT ditekan, abaikan sinyal api
    if (millis() < silenceUntil) {
      Serial.println("[ALARM] ⏳ Sinyal api diabaikan sementara (Masa Hening BOOT aktif).");
      return;
    }

    if (!isAlarmLatched) {
      isAlarmLatched = true;
      testAlarmUntil = 0;
      Serial.println("\n**************************************************************");
      Serial.println("🚨 🔥 BAHAYA API TERDETEKSI! ALARM TERKUNCI (LATCHED)!");
      Serial.println("🔔 Buzzer akan MENYALA TERUS MENERUS hingga Anda menekan");
      Serial.println("👉 tombol BOOT pada ESP32-C3 untuk mematikan alarm!");
      Serial.println("**************************************************************\n");
    }
    buzzerON();

  } else if (message.indexOf("\"alert\":false") >= 0 || 
             message.indexOf("ALARM_OFF") >= 0 || 
             message.indexOf("SAFE") >= 0) {
    
    // Jika alarm terkunci (Latched), ABAIKAN sinyal aman dari web!
    // Alarm tetap menyala sampai tombol BOOT ditekan manual oleh manusia di lokasi.
    if (!isAlarmLatched) {
      testAlarmUntil = 0;
      buzzerOFF();
    }
  }
}

// ==================== 7. PEMERIKSAAN TOMBOL BOOT FISIK ====================
void checkBootButton() {
  // Tombol BOOT aktif LOW saat ditekan (GPIO 9)
  if (digitalRead(BOOT_BUTTON_PIN) == LOW) {
    if (millis() - lastBtnPressTime > 250) { // Debounce 250ms
      lastBtnPressTime = millis();

      Serial.println("\n========================================================");
      Serial.println("[RESET MANUAL] >>> ✅ TOMBOL BOOT DITEKAN!");
      Serial.println("[RESET MANUAL] >>> Buzzer langsung DIMATIKAN seketika.");
      Serial.println("[RESET MANUAL] >>> Masa hening aktif selama 8 detik.");
      Serial.println("========================================================\n");

      isAlarmLatched = false;
      testAlarmUntil = 0;
      silenceUntil = millis() + 8000; // Jeda hening 8 detik agar tidak langsung memicu lagi
      
      // Matikan suara seketika
      buzzerOFF();
    }
  }
}

// ==================== 8. MANAJEMEN KONEKSI ====================
void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;

  Serial.print("[WIFI] Menghubungkan ke: ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(400);
    Serial.print(".");
    digitalWrite(LED_PIN, !digitalRead(LED_PIN));
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    digitalWrite(LED_PIN, HIGH);
    Serial.println("\n[WIFI] Terhubung!");
    Serial.print("[WIFI] Alamat IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n[WIFI] Gagal terhubung! Periksa SSID / Password.");
  }
}

void connectMQTT() {
  if (WiFi.status() != WL_CONNECTED) return;
  if (mqttClient.connected()) return;

  Serial.print("[MQTT] Menghubungkan ke Broker ");
  Serial.print(MQTT_BROKER);
  Serial.print("...");

  if (mqttClient.connect(CLIENT_ID)) {
    Serial.println(" Berhasil!");
    mqttClient.subscribe(MQTT_TOPIC);
    Serial.print("[MQTT] Berlangganan topik: ");
    Serial.println(MQTT_TOPIC);

    // Beep singkat konfirmasi koneksi
    buzzerON();
    delay(150);
    buzzerOFF();
  } else {
    Serial.print(" Gagal (Kode rc=");
    Serial.print(mqttClient.state());
    Serial.println(").");
  }
}

// ==================== 9. SETUP ====================
void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n========================================================");
  Serial.println("🔥 Flame Vision - ESP32-C3 Fire Alarm (Latch Mode)");
  Serial.println("👉 Tekan tombol BOOT di ESP32 untuk mematikan alarm");
  Serial.println("========================================================");

  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(LED_PIN, OUTPUT);
  pinMode(BOOT_BUTTON_PIN, INPUT_PULLUP); // Tombol BOOT GPIO 9
  buzzerOFF();

  // Uji Bunyi Fisik Buzzer Saat Awal Menyala (0.3 Detik)
  Serial.println("[TES AWAL] Menguji suara buzzer (300ms)...");
  buzzerON();
  delay(300);
  buzzerOFF();

  connectWiFi();

  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
  mqttClient.setCallback(onMqttMessage);
}

// ==================== 10. LOOP ====================
void loop() {
  // 1. Selalu periksa tombol BOOT fisik setiap saat
  checkBootButton();

  // 2. Reconnect WiFi berkala jika terputus
  if (WiFi.status() != WL_CONNECTED) {
    if (millis() - lastWifiRetry > 5000) {
      lastWifiRetry = millis();
      connectWiFi();
    }
  } else {
    // 3. Reconnect MQTT berkala jika terputus
    if (!mqttClient.connected()) {
      if (millis() - lastMqttRetry > 4000) {
        lastMqttRetry = millis();
        connectMQTT();
      }
    } else {
      mqttClient.loop();
    }
  }

  // 4. Kontrol Suara Buzzer
  if (isAlarmLatched) {
    // Alarm terkunci: Bunyi terus menerus sampai tombol BOOT ditekan
    buzzerON();
  } else if (testAlarmUntil > 0) {
    if (millis() < testAlarmUntil) {
      buzzerON();
    } else {
      testAlarmUntil = 0;
      buzzerOFF();
    }
  } else {
    buzzerOFF();
  }
}


