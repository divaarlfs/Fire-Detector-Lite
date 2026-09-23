import unittest
from src.mqtt_notifier import MQTTFireNotifier

class TestMQTTFireNotifier(unittest.TestCase):
    def test_mqtt_instance_and_status(self):
        notifier = MQTTFireNotifier(
            broker="76.13.19.250",
            port=1883,
            topic="test/flamevision/unit_test",
            enabled=False
        )
        status = notifier.get_status()
        self.assertFalse(status["enabled"])
        self.assertEqual(status["broker"], "76.13.19.250")
        self.assertEqual(status["port"], 1883)
        self.assertEqual(status["topic"], "test/flamevision/unit_test")

    def test_mqtt_update_config(self):
        notifier = MQTTFireNotifier(enabled=False)
        notifier.update_config(broker="76.13.19.250", port=1883, topic="custom/topic", enabled=False)
        status = notifier.get_status()
        self.assertEqual(status["broker"], "76.13.19.250")
        self.assertEqual(status["topic"], "custom/topic")

if __name__ == "__main__":
    unittest.main()
