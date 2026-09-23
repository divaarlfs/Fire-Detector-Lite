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

    def _is_valid_fire_region(self, roi_bgr: np.ndarray, roi_mask: np.ndarray, contour: np.ndarray, area: float) -> Tuple[bool, float]:
        """
        Validate fire candidate to reject non-fire yellow/orange objects.
        Analyzes:
        1. Peak Luminance & Intensity Variation (Fire has bright hot spots / glowing core).
        2. Red-to-Blue/Green dominance ratio.
        3. Contour irregularity / roughness (fire is non-uniform).
        """
        if roi_bgr.size == 0 or roi_mask.size == 0:
            return False, 0.0

        # Masked pixels only
        pixels_bgr = roi_bgr[roi_mask > 0]
        if len(pixels_bgr) < 20:
            return False, 0.0

        b = pixels_bgr[:, 0].astype(float)
        g = pixels_bgr[:, 1].astype(float)
        r = pixels_bgr[:, 2].astype(float)

        # 1. Fire must have strong Red channel dominance over Blue (cold colors)
        mean_r = np.mean(r)
        mean_g = np.mean(g)
        mean_b = np.mean(b)

        if mean_r < 150:  # Fire must have prominent red component
            return False, 0.0

        if (mean_r - mean_b) < 40:  # Yellow/orange objects with high blue/ambient are rejected
            return False, 0.0

        # 2. Hot-spot / Luminance Peak Check (Fire flames have bright core pixels)
        max_intensity = np.max(0.299 * r + 0.587 * g + 0.114 * b)
        std_intensity = np.std(0.299 * r + 0.587 * g + 0.114 * b)

        # Fire has hot core luminance (> 140)
        if max_intensity < 140:
            return False, 0.0

        # 3. Contour Shape / Roughness Check
        perimeter = cv2.arcLength(contour, True)
        if perimeter > 0:
            # Compactness / Circularity measure (4 * pi * area / perimeter^2)
            circularity = (4 * np.pi * area) / (perimeter * perimeter)
            # Highly uniform & smooth circle/square without any internal gradient
            if circularity > 0.92 and std_intensity < 5.0 and area > 1500:
                return False, 0.0

        # Calculate robust confidence score
        lum_score = min(1.0, max_intensity / 255.0)
        red_diff_score = min(1.0, (mean_r - mean_b) / 160.0)
        texture_score = min(1.0, (std_intensity + 5.0) / 40.0)

        confidence = (0.4 * lum_score) + (0.35 * red_diff_score) + (0.25 * texture_score)
        return True, float(np.clip(confidence, 0.45, 0.99))

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
            if area >= self.min_contour_area and area < (frame_area * 0.95):
                x, y, w, h = cv2.boundingRect(cnt)

                roi_bgr = frame[y : y + h, x : x + w]
                roi_mask = clean_mask[y : y + h, x : x + w]

                # Validate whether candidate is real flame or plain colored object
                is_valid, confidence = self._is_valid_fire_region(roi_bgr, roi_mask, cnt, area)

                if is_valid:
                    detections.append({
                        "bbox": (x, y, w, h),
                        "area": area,
                        "confidence": confidence,
                        "contour": cnt,
                    })

        is_fire_detected = len(detections) > 0
        return is_fire_detected, detections, clean_mask
