"""
UI rendering, annotation utilities, HUD drawing, and audio alert helpers.
"""

import threading
import time
from typing import List, Dict, Any, Optional
import cv2
import numpy as np

# Windows sound notification support
try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

_last_beep_time = 0.0
_beep_lock = threading.Lock()


def trigger_audio_alert(frequency: int = 2500, duration_ms: int = 200, cooldown_sec: float = 0.8) -> None:
    """
    Triggers an audio beep alarm on a separate thread without blocking the main video loop.
    """
    global _last_beep_time
    current_time = time.time()

    if not HAS_WINSOUND:
        return

    with _beep_lock:
        if current_time - _last_beep_time < cooldown_sec:
            return
        _last_beep_time = current_time

    def _beep_worker():
        try:
            winsound.Beep(frequency, duration_ms)
        except Exception:
            pass

    threading.Thread(target=_beep_worker, daemon=True).start()


def draw_fire_boxes(
    frame: np.ndarray,
    detections: List[Dict[str, Any]],
    is_fire_detected: bool,
    fps: float = 0.0,
    show_hud: bool = True,
    show_fps: bool = True,
) -> np.ndarray:
    """
    Renders stylish bounding boxes with 'FIRE DETECTED' labels, corner accents,
    confidence metrics, and a top-level alert HUD banner.
    """
    annotated = frame.copy()
    h, w = annotated.shape[:2]

    # Draw each fire bounding box
    for det in detections:
        x, y, bw, bh = det["bbox"]
        confidence = det.get("confidence", 1.0)
        conf_pct = int(confidence * 100)

        # 1. Main Bounding Box (Vibrant Red)
        box_color = (20, 20, 235)  # BGR: Bright Red
        thickness = 2
        cv2.rectangle(annotated, (x, y), (x + bw, y + bh), box_color, thickness)

        # 2. Corner Bracket Accents for Modern HUD Look
        corner_length = min(18, max(8, bw // 4, bh // 4))
        accent_color = (0, 140, 255)  # Orange-Red Accent
        # Top-left
        cv2.line(annotated, (x, y), (x + corner_length, y), accent_color, 3)
        cv2.line(annotated, (x, y), (x, y + corner_length), accent_color, 3)
        # Top-right
        cv2.line(annotated, (x + bw, y), (x + bw - corner_length, y), accent_color, 3)
        cv2.line(annotated, (x + bw, y), (x + bw, y + corner_length), accent_color, 3)
        # Bottom-left
        cv2.line(annotated, (x, y + bh), (x + corner_length, y + bh), accent_color, 3)
        cv2.line(annotated, (x, y + bh), (x, y + bh - corner_length), accent_color, 3)
        # Bottom-right
        cv2.line(annotated, (x + bw, y + bh), (x + bw - corner_length, y + bh), accent_color, 3)
        cv2.line(annotated, (x + bw, y + bh), (x + bw, y + bh - corner_length), accent_color, 3)

        # 3. Label Badge: 'FIRE DETECTED'
        label_text = f"FIRE DETECTED ({conf_pct}%)"
        font = cv2.FONT_HERSHEY_DUPLEX
        font_scale = 0.55
        font_thick = 1

        (text_w, text_h), baseline = cv2.getTextSize(label_text, font, font_scale, font_thick)

        # Badge position (above box if space permits, otherwise inside)
        badge_y1 = max(0, y - text_h - 10)
        badge_y2 = y if y >= text_h + 10 else y + text_h + 10
        badge_x1 = x
        badge_x2 = x + text_w + 14

        # Background badge fill
        cv2.rectangle(annotated, (badge_x1, badge_y1), (badge_x2, badge_y2), (0, 0, 200), -1)
        cv2.rectangle(annotated, (badge_x1, badge_y1), (badge_x2, badge_y2), (50, 50, 255), 1)

        # Label Text
        text_origin = (badge_x1 + 6, badge_y2 - 5 if y >= text_h + 10 else badge_y2 - 4)
        cv2.putText(
            annotated,
            label_text,
            text_origin,
            font,
            font_scale,
            (255, 255, 255),
            font_thick,
            cv2.LINE_AA,
        )

    if show_hud:
        # Top HUD Status Banner
        hud_height = 42
        hud_overlay = annotated.copy()

        if is_fire_detected:
            # Flashing/Solid Alert Red Header
            cv2.rectangle(hud_overlay, (0, 0), (w, hud_height), (0, 0, 180), -1)
            cv2.addWeighted(hud_overlay, 0.75, annotated, 0.25, 0, annotated)

            # Banner border
            cv2.line(annotated, (0, hud_height), (w, hud_height), (0, 0, 255), 2)

            status_text = f"[!] WARNING: FIRE DETECTED ({len(detections)} REGIONS)"
            status_color = (255, 255, 255)
        else:
            # Subtle Dark Glass Header (Normal Status)
            cv2.rectangle(hud_overlay, (0, 0), (w, hud_height), (20, 25, 25), -1)
            cv2.addWeighted(hud_overlay, 0.65, annotated, 0.35, 0, annotated)

            cv2.line(annotated, (0, hud_height), (w, hud_height), (40, 60, 40), 1)

            status_text = "[STATUS: NORMAL] - Scanning for fire..."
            status_color = (80, 230, 120)

        cv2.putText(
            annotated,
            status_text,
            (16, 28),
            cv2.FONT_HERSHEY_DUPLEX,
            0.65,
            status_color,
            1,
            cv2.LINE_AA,
        )

    if show_fps:
        fps_text = f"FPS: {fps:4.1f}"
        cv2.putText(
            annotated,
            fps_text,
            (w - 110, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (220, 220, 220),
            1,
            cv2.LINE_AA,
        )

    return annotated


def create_side_by_side_view(original_frame: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """
    Creates a split-screen view showing original annotated frame on the left
    and the processed binary/colorized fire mask on the right.
    """
    h, w = original_frame.shape[:2]

    # Convert 1-channel mask to 3-channel color map
    if len(mask.shape) == 2:
        mask_color = cv2.applyColorMap(mask, cv2.COLORMAP_INFERNO)
    else:
        mask_color = mask

    # Resize mask to match original frame height if needed
    if mask_color.shape[:2] != (h, w):
        mask_color = cv2.resize(mask_color, (w, h))

    # Add label on mask view
    cv2.putText(
        mask_color,
        "DEBUG MASK VIEW (INFERNO)",
        (16, 30),
        cv2.FONT_HERSHEY_DUPLEX,
        0.6,
        (255, 255, 255),
        1,
        cv2.LINE_AA,
    )

    combined = np.hstack((original_frame, mask_color))
    return combined
