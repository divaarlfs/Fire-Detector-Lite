"""
MQTT Notifier module for Fire-Detector-Lite (FlameVision AI).
Connects to an MQTT Broker and broadcasts fire alarm signals to IoT devices
like the ESP32-C3 Mini Buzzer.
"""

import json
import time
import threading
from typing import Dict, Any, Optional

try:
    import paho.mqtt.client as mqtt
    HAS_MQTT = True
except ImportError:
    HAS_MQTT = False


class MQTTFireNotifier:
    def __init__(
        self,
        broker: str = "76.13.19.250",
        port: int = 1883,
        topic: str = "flamevision/fire_alert",
        client_id: Optional[str] = None,
        enabled: bool = True,
        cooldown_sec: float = 1.0,
    ):
        self.broker = broker
        self.port = port
        self.topic = topic
        self.client_id = client_id or f"flamevision_server_{int(time.time())}"
        self.enabled = enabled
        self.cooldown_sec = cooldown_sec

        self.client: Optional[Any] = None
        self.is_connected = False
        self._lock = threading.Lock()
        self._last_publish_time = 0.0
        self._last_state: Optional[bool] = None

        if HAS_MQTT and self.enabled:
            self.start()

    def start(self):
        """Starts the MQTT client loop on a background thread."""
        if not HAS_MQTT or not self.enabled:
            return

        with self._lock:
            if self.client is not None:
                try:
                    self.client.loop_stop()
                    self.client.disconnect()
                except Exception:
                    pass

            try:
                # paho-mqtt v2 and v1 compatibility
                if hasattr(mqtt, "CallbackAPIVersion"):
                    self.client = mqtt.Client(
                        mqtt.CallbackAPIVersion.VERSION2,
                        client_id=self.client_id
                    )
                else:
                    self.client = mqtt.Client(client_id=self.client_id)

                self.client.on_connect = self._on_connect
                self.client.on_disconnect = self._on_disconnect

                # Non-blocking connection in worker thread
                def _connect_worker():
                    try:
                        self.client.connect(self.broker, self.port, keepalive=60)
                        self.client.loop_start()
                    except Exception as e:
                        print(f"[MQTT] Connection to {self.broker}:{self.port} failed: {e}")
                        self.is_connected = False

                threading.Thread(target=_connect_worker, daemon=True).start()
            except Exception as e:
                print(f"[MQTT] Setup error: {e}")
                self.is_connected = False

    def stop(self):
        """Disconnects and stops MQTT client loop."""
        with self._lock:
            if self.client is not None:
                try:
                    self.client.loop_stop()
                    self.client.disconnect()
                except Exception:
                    pass
                self.client = None
            self.is_connected = False

    def _on_connect(self, client, userdata, flags, rc, *args):
        if rc == 0:
            self.is_connected = True
            print(f"[MQTT] Connected successfully to broker {self.broker}:{self.port}")
        else:
            self.is_connected = False
            print(f"[MQTT] Connection failed with code {rc}")

    def _on_disconnect(self, client, userdata, rc, *args):
        self.is_connected = False
        print(f"[MQTT] Disconnected from broker {self.broker}")

    def update_config(self, broker: str, port: int, topic: str, enabled: bool):
        """Updates broker configurations and reconnects if necessary."""
        reconnect = (
            broker != self.broker
            or port != self.port
            or enabled != self.enabled
        )
        self.broker = broker
        self.port = port
        self.topic = topic
        self.enabled = enabled

        if reconnect:
            if self.enabled:
                self.start()
            else:
                self.stop()

    def get_status(self) -> Dict[str, Any]:
        """Returns current MQTT configuration and connection state."""
        return {
            "has_mqtt_lib": HAS_MQTT,
            "enabled": self.enabled,
            "connected": self.is_connected,
            "broker": self.broker,
            "port": self.port,
            "topic": self.topic,
            "client_id": self.client_id,
        }

    def publish_fire_alert(
        self,
        is_fire: bool,
        fire_count: int = 0,
        confidence: float = 0.0,
        force: bool = False
    ) -> bool:
        """
        Publishes fire alert payload to ESP32-C3 Buzzer.
        """
        if not self.enabled or not self.client or not self.is_connected:
            return False

        current_time = time.time()
        # Publish if state changed, or if fire is continuing after cooldown
        state_changed = (self._last_state != is_fire)
        if not force and not state_changed and (current_time - self._last_publish_time < self.cooldown_sec):
            return False

        self._last_publish_time = current_time
        self._last_state = is_fire

        payload = {
            "alert": is_fire,
            "status": "FIRE_DETECTED" if is_fire else "SAFE",
            "command": "ALARM_MILITARY_ON" if is_fire else "ALARM_OFF",
            "count": fire_count,
            "confidence": round(float(confidence), 1),
            "timestamp": int(current_time),
        }

        try:
            payload_str = json.dumps(payload)
            info = self.client.publish(self.topic, payload_str, qos=0)
            return info.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            print(f"[MQTT] Publish error: {e}")
            return False

    def publish_test_alarm(self) -> bool:
        """Sends a test alarm trigger payload to the ESP32-C3 Buzzer."""
        if not self.client or not self.is_connected:
            return False

        payload = {
            "alert": True,
            "status": "TEST_TRIGGER",
            "command": "TEST_BUZZER",
            "count": 1,
            "confidence": 99.9,
            "timestamp": int(time.time()),
        }

        try:
            payload_str = json.dumps(payload)
            info = self.client.publish(self.topic, payload_str, qos=0)
            return info.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            print(f"[MQTT] Test publish error: {e}")
            return False
