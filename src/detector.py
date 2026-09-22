"""
Fire Detector module implementing multi-color space analysis (HSV and RGB/YCrCb)
and morphological contour filtering to detect fire/flames in real-time.
"""

from typing import List, Dict, Tuple, Any
import cv2
import numpy as np


class FireDetector:
    """
    Detects fire in video frames using color segmentation (HSV + YCrCb/RGB heuristics)
    and morphological shape processing.
    """

    def __init__(
        self,
        min_contour_area: int = 600,
        h_min: int = 0,
        h_max: int = 25,
        s_min: int = 100,
        s_max: int = 255,
        v_min: int = 190,
        v_max: int = 255,
        blur_kernel_size: int = 15,
    ):
        """
        Initialize the Fire Detector with tunable threshold parameters.
        """
        self.min_contour_area = min_contour_area
        self.h_min = h_min
        self.h_max = h_max
        self.s_min = s_min
        self.s_max = s_max
        self.v_min = v_min
        self.v_max = v_max
        self.blur_kernel_size = blur_kernel_size if blur_kernel_size % 2 == 1 else blur_kernel_size + 1

    def update_params(self, **kwargs: Any) -> None:
        """Update detector parameters dynamically (e.g. from trackbars)."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                if key == "blur_kernel_size" and value % 2 == 0:
                    value = max(1, value + 1)
                setattr(self, key, value)

    def compute_fire_mask(self, frame: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Computes the binary fire mask using dual color-space filtering:
        1. HSV Color Range (warm flame colors: Red/Orange/Yellow)
        2. RGB/YCrCb Rules (R > G + 15, G > B + 10, R > 150, Cr > Cb)
        """
        if frame is None or frame.size == 0 or np.mean(frame) < 5:
            empty = np.zeros(frame.shape[:2] if frame is not None else (100, 100), dtype=np.uint8)
            return empty, empty

        # Apply Gaussian Blur to smooth noise
        k = max(3, self.blur_kernel_size if self.blur_kernel_size % 2 == 1 else self.blur_kernel_size + 1)
        blurred = cv2.GaussianBlur(frame, (k, k), 0)

        # 1. HSV Color Space Mask
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
        lower_hsv = np.array([self.h_min, self.s_min, self.v_min], dtype=np.uint8)
        upper_hsv = np.array([self.h_max, self.s_max, self.v_max], dtype=np.uint8)
        mask_hsv = cv2.inRange(hsv, lower_hsv, upper_hsv)

        # 2. RGB and YCrCb Heuristic Rule
        # Fire characteristic: Strong Red dominance, High Luminance, and Cr > Cb
        b, g, r = cv2.split(blurred)
        ycrcb = cv2.cvtColor(blurred, cv2.COLOR_BGR2YCrCb)
        y, cr, cb = cv2.split(ycrcb)

        rgb_rule = (r.astype(int) > g.astype(int) + 15) & (g.astype(int) > b.astype(int) + 10) & (r > 150)
        ycrcb_rule = (cr > cb + 10) & (y > 100)
        mask_rules = (rgb_rule & ycrcb_rule).astype(np.uint8) * 255

        # Combined Mask
        combined_mask = cv2.bitwise_and(mask_hsv, mask_rules)

        # 3. Morphological Operations to clean noise and bridge flame patches
        kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))

        mask_clean = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel_open)
        mask_clean = cv2.dilate(mask_clean, kernel_dilate, iterations=2)

        return mask_clean, combined_mask

    def detect(self, frame: np.ndarray) -> Tuple[bool, List[Dict[str, Any]], np.ndarray]:
        """
        Process a single image frame and return detection results.

        Returns:
            - is_fire_detected (bool): True if at least one valid fire contour is found.
            - detections (list of dict): List containing bounding box (x, y, w, h), area, and confidence.
            - mask (np.ndarray): Binary mask of detected fire regions.
        """
        if frame is None or frame.size == 0:
            return False, [], np.zeros((100, 100), dtype=np.uint8)

        clean_mask, _ = self.compute_fire_mask(frame)

        # Find external contours
        contours, _ = cv2.findContours(clean_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        detections: List[Dict[str, Any]] = []

        frame_area = frame.shape[0] * frame.shape[1]

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area >= self.min_contour_area:
                x, y, w, h = cv2.boundingRect(cnt)
                
                # Aspect ratio & area sanity check (avoid full screen false positives)
                if area < (frame_area * 0.95):
                    # Compute confidence based on area and pixel density inside contour
                    roi_mask = clean_mask[y : y + h, x : x + w]
                    pixel_density = cv2.countNonZero(roi_mask) / (w * h) if (w * h) > 0 else 0
                    confidence = min(1.0, 0.4 + (pixel_density * 0.6))

                    detections.append({
                        "bbox": (x, y, w, h),
                        "area": area,
                        "confidence": float(confidence),
                        "contour": cnt,
                    })

        is_fire_detected = len(detections) > 0
        return is_fire_detected, detections, clean_mask
