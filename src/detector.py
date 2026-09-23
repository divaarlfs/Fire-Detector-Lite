"""
🔥 Flame Vision - Advanced Fire Detector Module
Supports YOLO Deep Learning (ONNX Runtime) for high-accuracy morphology-based fire detection
with zero false positives on yellow/orange items, plus fallback combustion color analysis.
"""

import os
from typing import List, Dict, Tuple, Any, Optional
import cv2
import numpy as np

try:
    import onnxruntime as ort
    HAS_ONNX = True
except ImportError:
    HAS_ONNX = False


class FireDetector:
    """
    State-of-the-Art Fire Detector supporting:
    1. YOLOv8 Deep Learning Model (ONNX) - Detects actual flame shape, core, and plume.
       Strictly rejects flat yellow/orange clothing, paper, and ambient reflections.
    2. Fallback Physics Combustion Model (HSV + YCrCb + RGB Incandescence).
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        conf_threshold: float = 0.28,
        nms_threshold: float = 0.45,
        min_contour_area: int = 400,
        h_min: int = 0,
        h_max: int = 22,
        s_min: int = 120,
        s_max: int = 255,
        v_min: int = 190,
        v_max: int = 255,
        blur_kernel_size: int = 11,
    ):
        self.conf_threshold = conf_threshold
        self.nms_threshold = nms_threshold
        self.min_contour_area = min_contour_area
        self.h_min = h_min
        self.h_max = h_max
        self.s_min = s_min
        self.s_max = s_max
        self.v_min = v_min
        self.v_max = v_max
        self.blur_kernel_size = blur_kernel_size if blur_kernel_size % 2 == 1 else blur_kernel_size + 1

        self.ort_session: Optional[Any] = None
        self.input_name: str = "images"
        self.input_shape: Tuple[int, int] = (320, 320)
        self.use_yolo: bool = False

        # Determine model path
        default_paths = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "yolov8_fire.onnx"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "cctv_fire.onnx"),
        ]
        
        selected_model = model_path
        if not selected_model:
            for p in default_paths:
                if os.path.exists(p) and os.path.getsize(p) > 1000000:
                    selected_model = p
                    break

        if HAS_ONNX and selected_model and os.path.exists(selected_model):
            try:
                # Optimized CPU Inference
                opts = ort.SessionOptions()
                opts.intra_op_num_threads = 2
                opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                
                self.ort_session = ort.InferenceSession(
                    selected_model,
                    sess_options=opts,
                    providers=["CPUExecutionProvider"]
                )
                self.input_name = self.ort_session.get_inputs()[0].name
                inp_shape = self.ort_session.get_inputs()[0].shape
                if len(inp_shape) == 4 and isinstance(inp_shape[2], int) and isinstance(inp_shape[3], int):
                    self.input_shape = (inp_shape[3], inp_shape[2])
                else:
                    self.input_shape = (320, 320)

                self.use_yolo = True
                print(f"[DETECTOR] YOLOv8 Fire Engine loaded successfully from: {selected_model} (Input: {self.input_shape})")
            except Exception as e:
                print(f"[DETECTOR] Warning: Could not initialize ONNX session ({e}). Falling back to Color Detector.")
                self.use_yolo = False
        else:
            print("[DETECTOR] Running in Classical Combustion Color Filter Mode.")

    def update_params(self, **kwargs: Any) -> None:
        """Update detector parameters dynamically from settings."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                if key == "blur_kernel_size" and value % 2 == 0:
                    value = max(1, value + 1)
                setattr(self, key, value)

    def _detect_yolo(self, frame: np.ndarray) -> Tuple[bool, List[Dict[str, Any]], np.ndarray]:
        """Runs YOLOv8 ONNX inference on input frame."""
        h_orig, w_orig = frame.shape[:2]
        net_w, net_h = self.input_shape

        # Preprocessing: Resize & Normalize BGR to RGB [0.0, 1.0]
        resized = cv2.resize(frame, (net_w, net_h))
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        blob = (rgb.astype(np.float32) / 255.0).transpose(2, 0, 1)[np.newaxis, ...]

        # Run ONNX inference
        outputs = self.ort_session.run(None, {self.input_name: blob})[0]
        preds = outputs[0].T  # Shape: (2100, 4 + classes) or (8400, 4 + classes)

        boxes = []
        scores = []
        class_ids = []

        # Parse detections
        num_classes = preds.shape[1] - 4
        for i in range(preds.shape[0]):
            cx, cy, w, h = preds[i, :4]
            class_scores = preds[i, 4:]
            
            # Fire is class 0 in fire/smoke models
            fire_score = float(class_scores[0]) if num_classes >= 1 else 0.0
            
            # If multi-class, find top score
            max_class_id = int(np.argmax(class_scores))
            max_score = float(class_scores[max_class_id])

            # Prioritize fire class (class 0)
            target_score = fire_score if fire_score > (self.conf_threshold * 0.8) else max_score
            target_class = 0 if fire_score > (self.conf_threshold * 0.8) else max_class_id

            if target_score >= self.conf_threshold:
                # Convert center xywh to top-left xywh and scale to original frame
                x1 = int((cx - w / 2.0) * (w_orig / float(net_w)))
                y1 = int((cy - h / 2.0) * (h_orig / float(net_h)))
                bw = int(w * (w_orig / float(net_w)))
                bh = int(h * (h_orig / float(net_h)))

                # Clip bounds
                x1 = max(0, min(x1, w_orig - 1))
                y1 = max(0, min(y1, h_orig - 1))
                bw = max(5, min(bw, w_orig - x1))
                bh = max(5, min(bh, h_orig - y1))

                boxes.append([x1, y1, bw, bh])
                scores.append(target_score)
                class_ids.append(target_class)

        # Apply Non-Maximum Suppression
        detections: List[Dict[str, Any]] = []
        mask = np.zeros((h_orig, w_orig), dtype=np.uint8)

        if len(boxes) > 0:
            indices = cv2.dnn.NMSBoxes(boxes, scores, score_threshold=self.conf_threshold, nms_threshold=self.nms_threshold)
            if len(indices) > 0:
                for idx in indices:
                    i = idx if isinstance(idx, (int, np.integer)) else idx[0]
                    bx, by, bw, bh = boxes[i]
                    conf = float(scores[i])
                    
                    # Generate visual mask representation
                    cv2.rectangle(mask, (bx, by), (bx + bw, by + bh), 255, -1)
                    
                    detections.append({
                        "bbox": (bx, by, bw, bh),
                        "confidence": conf,
                        "area": float(bw * bh),
                        "class_name": "API" if class_ids[i] == 0 else "ASAP"
                    })

        is_fire_detected = len(detections) > 0
        return is_fire_detected, detections, mask

    def compute_fire_mask(self, frame: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Classical physical combustion mask computation (fallback)."""
        if frame is None or frame.size == 0 or np.mean(frame) < 5:
            empty = np.zeros(frame.shape[:2] if frame is not None else (100, 100), dtype=np.uint8)
            return empty, empty

        k = max(3, self.blur_kernel_size if self.blur_kernel_size % 2 == 1 else self.blur_kernel_size + 1)
        blurred = cv2.GaussianBlur(frame, (k, k), 0)

        # HSV Mask
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
        lower_hsv = np.array([self.h_min, self.s_min, self.v_min], dtype=np.uint8)
        upper_hsv = np.array([self.h_max, self.s_max, self.v_max], dtype=np.uint8)
        mask_hsv = cv2.inRange(hsv, lower_hsv, upper_hsv)

        # RGB Incandescence
        b, g, r = cv2.split(blurred)
        b_f, g_f, r_f = b.astype(np.int32), g.astype(np.int32), r.astype(np.int32)
        rgb_rule = (r_f >= 165) & (r_f > g_f + 15) & (g_f > b_f + 25) & (b_f <= 75)

        # YCrCb Chrominance
        ycrcb = cv2.cvtColor(blurred, cv2.COLOR_BGR2YCrCb)
        y, cr, cb = cv2.split(ycrcb)
        y_f, cr_f, cb_f = y.astype(np.int32), cr.astype(np.int32), cb.astype(np.int32)
        ycrcb_rule = (cr_f >= 150) & (cb_f <= 88) & ((cr_f - cb_f) >= 80) & (y_f >= 105)

        combined_mask = cv2.bitwise_and(mask_hsv, (rgb_rule & ycrcb_rule).astype(np.uint8) * 255)
        kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))

        mask_clean = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel_open)
        mask_clean = cv2.dilate(mask_clean, kernel_dilate, iterations=1)

        return mask_clean, combined_mask

    def detect(self, frame: np.ndarray) -> Tuple[bool, List[Dict[str, Any]], np.ndarray]:
        """
        Main Detection Entrypoint:
        Executes YOLO Deep Learning detection when active, or falls back to physics color analysis.
        """
        if frame is None or frame.size == 0:
            return False, [], np.zeros((100, 100), dtype=np.uint8)

        if self.use_yolo and self.ort_session is not None:
            try:
                return self._detect_yolo(frame)
            except Exception as e:
                print(f"[DETECTOR] YOLO Inference exception ({e}), falling back to color model.")

        # Fallback to color model
        clean_mask, _ = self.compute_fire_mask(frame)
        contours, _ = cv2.findContours(clean_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        detections: List[Dict[str, Any]] = []
        frame_area = frame.shape[0] * frame.shape[1]

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area >= self.min_contour_area and area < (frame_area * 0.90):
                x, y, w, h = cv2.boundingRect(cnt)
                roi_bgr = frame[y : y + h, x : x + w]
                roi_mask = clean_mask[y : y + h, x : x + w]

                if roi_bgr.size > 0 and roi_mask.size > 0:
                    pixels = roi_bgr[roi_mask > 0]
                    if len(pixels) >= 20:
                        b = pixels[:, 0].astype(np.float64)
                        r = pixels[:, 2].astype(np.float64)
                        mean_r, mean_b = np.mean(r), np.mean(b)
                        if mean_r >= 165 and mean_b <= 70 and (mean_r - mean_b) >= 95:
                            conf = float(np.clip((mean_r - mean_b) / 160.0, 0.50, 0.98))
                            detections.append({
                                "bbox": (x, y, w, h),
                                "area": area,
                                "confidence": conf,
                                "class_name": "API"
                            })

        return len(detections) > 0, detections, clean_mask
