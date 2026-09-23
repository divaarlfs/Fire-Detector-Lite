import os
import sys
import unittest
import numpy as np
import cv2

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.detector import FireDetector
from src.utils import draw_fire_boxes, create_side_by_side_view


class TestFireDetector(unittest.TestCase):

    def setUp(self):
        self.detector = FireDetector()

    def test_no_fire_detected_on_blank_frame(self):
        """A plain dark/blue image should not trigger fire detection."""
        blank_frame = np.full((400, 600, 3), (200, 50, 20), dtype=np.uint8)
        is_fire, detections, mask = self.detector.detect(blank_frame)

        self.assertFalse(is_fire)
        self.assertEqual(len(detections), 0)

    def test_fire_detected_on_real_fire_video(self):
        """Real fire frame from sample_fire.mp4 should be detected with high confidence."""
        video_path = os.path.join(os.path.dirname(__file__), "..", "sample_fire.mp4")
        if os.path.exists(video_path):
            cap = cv2.VideoCapture(video_path)
            cap.set(cv2.CAP_PROP_POS_FRAMES, 60)
            ret, frame = cap.read()
            cap.release()

            if ret and frame is not None:
                is_fire, detections, mask = self.detector.detect(frame)
                self.assertTrue(is_fire, "Fire should be detected in real fire video frame")
                self.assertGreaterEqual(len(detections), 1)
                self.assertGreater(detections[0]["confidence"], 0.20)

    def test_reject_ambient_yellow_and_orange_objects(self):
        """Standard yellow/orange geometric items (clothing, paper) must be rejected by YOLO."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # Yellow rectangle
        yellow_obj = (0, 215, 255)
        cv2.rectangle(frame, (50, 50), (220, 220), yellow_obj, -1)

        # Orange rectangle
        orange_obj = (0, 140, 255)
        cv2.rectangle(frame, (280, 50), (450, 220), orange_obj, -1)

        is_fire, detections, mask = self.detector.detect(frame)
        self.assertFalse(is_fire, "Non-fire yellow/orange flat objects must be rejected by YOLO")
        self.assertEqual(len(detections), 0)

    def test_color_fallback_mode(self):
        """Verify color-based fallback detection works when YOLO is disabled."""
        color_detector = FireDetector(model_path="non_existent_model.onnx")
        self.assertFalse(color_detector.use_yolo)

        # Blank test
        blank = np.zeros((400, 600, 3), dtype=np.uint8)
        is_fire, dets, mask = color_detector.detect(blank)
        self.assertFalse(is_fire)

    def test_parameter_updates(self):
        """Verify dynamic parameter updating."""
        self.detector.update_params(h_min=10, min_contour_area=800, conf_threshold=0.35)
        self.assertEqual(self.detector.h_min, 10)
        self.assertEqual(self.detector.min_contour_area, 800)
        self.assertEqual(self.detector.conf_threshold, 0.35)

    def test_draw_fire_boxes_and_side_by_side(self):
        """Verify rendering utilities output expected shape."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_detections = [{
            "bbox": (100, 100, 80, 80),
            "area": 6400,
            "confidence": 0.92,
        }]

        annotated = draw_fire_boxes(frame, mock_detections, is_fire_detected=True, fps=30.0)
        self.assertEqual(annotated.shape, frame.shape)

        mask = np.zeros((480, 640), dtype=np.uint8)
        split_view = create_side_by_side_view(annotated, mask)
        self.assertEqual(split_view.shape, (480, 1280, 3))


if __name__ == "__main__":
    unittest.main()
