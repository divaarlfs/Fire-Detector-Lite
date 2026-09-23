"""
Skrip Pengujian MQTT Subscriber untuk FlameVision AI
Menerima dan menampilkan data notifikasi alarm api dari Broker MQTT secara real-time.
"""

import sys
import json
import time

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("[ERROR] Library 'paho-mqtt' belum terpasang. Jalankan: pip install paho-mqtt")
    sys.exit(1)

BROKER = "76.13.19.250"
PORT = 1883
TOPIC = "flamevision/fire_alert"


def on_connect(client, userdata, flags, rc, *args):
    if rc == 0:
        print("=" * 60)
        print(f"[OK] Berhasil terhubung ke Broker MQTT: {BROKER}:{PORT}")
        print(f"[OK] Berlangganan topik: '{TOPIC}'")
        print("Menunggu data deteksi api dari server FlameVision AI...")
        print("=" * 60)
        client.subscribe(TOPIC)
    else:
        print(f"[ERROR] Gagal terhubung ke broker. Kode RC: {rc}")


def on_message(client, userdata, msg):
    try:
        topic = msg.topic
        raw_payload = msg.payload.decode('utf-8')
        print(f"\n[{time.strftime('%H:%M:%S')}] Pesan Masuk di Topik '{topic}':")
        
        # Coba parse sebagai JSON terstruktur
        try:
            data = json.loads(raw_payload)
            is_alert = data.get("alert", False)
            status = data.get("status", "UNKNOWN")
            command = data.get("command", "-")
            count = data.get("count", 0)
            confidence = data.get("confidence", 0.0)

            if is_alert:
                print("  🔥 STATUS      : [BAHAYA - API TERDETEKSI]")
            else:
                print("  ✅ STATUS      : [AMAN / NORMAL]")
            
            print(f"  📢 Command     : {command}")
            print(f"  🎯 Titik Api   : {count} Region")
            print(f"  📊 Keyakinan   : {confidence}%")
            print(f"  📦 Raw Payload : {raw_payload}")
        except json.JSONDecodeError:
            print(f"  📦 Raw Message : {raw_payload}")

    except Exception as e:
        print(f"[ERROR] Gagal memproses pesan: {e}")


def main():
    print(f"Menghubungkan ke broker {BROKER}:{PORT}...")
    
    # Kompatibilitas paho-mqtt v1 dan v2
    if hasattr(mqtt, "CallbackAPIVersion"):
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="flamevision_subscriber_test")
    else:
        client = mqtt.Client(client_id="flamevision_subscriber_test")

    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(BROKER, PORT, keepalive=60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Berhenti memantau MQTT.")
        client.disconnect()
    except Exception as e:
        print(f"[ERROR] Gagal terhubung: {e}")


if __name__ == "__main__":
    main()
