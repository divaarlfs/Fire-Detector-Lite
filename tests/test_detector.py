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
        self.detector = FireDetector(min_contour_area=200)

    def test_no_fire_detected_on_blank_frame(self):
        """A plain dark/blue image should not trigger fire detection."""
        # Blue background (BGR: 200, 50, 20)
        blank_frame = np.full((400, 600, 3), (200, 50, 20), dtype=np.uint8)
        is_fire, detections, mask = self.detector.detect(blank_frame)

        self.assertFalse(is_fire)
        self.assertEqual(len(detections), 0)
        self.assertEqual(cv2.countNonZero(mask), 0)

    def test_fire_detected_on_synthetic_flame(self):
        """A synthetic frame with bright orange-red fire color patch should be detected."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # Draw a synthetic flame polygon with fire color (BGR: B=10, G=120, R=255)
        # HSV equivalent: H ~ 13, S ~ 245, V ~ 255 (within fire flame range)
        flame_color = (15, 120, 255)  # Bright orange-red
        cv2.rectangle(frame, (200, 150), (350, 300), flame_color, -1)

        is_fire, detections, mask = self.detector.detect(frame)

        self.assertTrue(is_fire, "Fire should be detected in synthetic flame frame")
        self.assertGreaterEqual(len(detections), 1)

        # Verify bounding box is around the synthetic flame
        det = detections[0]
        x, y, w, h = det["bbox"]
        self.assertGreaterEqual(x, 180)
        self.assertLessEqual(x + w, 370)
        self.assertGreaterEqual(y, 130)
        self.assertLessEqual(y + h, 320)
        self.assertGreater(det["confidence"], 0.0)

    def test_parameter_updates(self):
        """Verify dynamic parameter updating."""
        self.detector.update_params(h_min=10, min_contour_area=800)
        self.assertEqual(self.detector.h_min, 10)
        self.assertEqual(self.detector.min_contour_area, 800)

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
