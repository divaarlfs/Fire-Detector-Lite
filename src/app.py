"""
Main Application Controller for Real-Time Fire Detection with OpenCV.
"""

import os
import time
from typing import Optional, Union
import cv2
import numpy as np

from .detector import FireDetector
from .utils import draw_fire_boxes, trigger_audio_alert, create_side_by_side_view


class FireDetectionApp:
    """
    Manages video capture, processing loop, UI interactions, snapshots, and controls.
    """

    def __init__(
        self,
        source: Union[int, str] = 0,
        enable_audio: bool = True,
        show_debug: bool = False,
        window_title: str = "Real-Time Fire Detection System - OpenCV",
    ):
        self.source = source
        self.enable_audio = enable_audio
        self.show_debug = show_debug
        self.window_title = window_title

        self.detector = FireDetector()
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_running = False
        self.is_paused = False
        self.show_trackbars = False
        self.trackbar_window = "Sensitivity Settings"
        self.snapshots_dir = os.path.join(os.getcwd(), "snapshots")

        os.makedirs(self.snapshots_dir, exist_ok=True)

    def _init_trackbars(self) -> None:
        """Create trackbar window to tune HSV and threshold parameters in real-time."""
        cv2.namedWindow(self.trackbar_window, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.trackbar_window, 400, 320)

        cv2.createTrackbar("H Min", self.trackbar_window, self.detector.h_min, 179, lambda v: self.detector.update_params(h_min=v))
        cv2.createTrackbar("H Max", self.trackbar_window, self.detector.h_max, 179, lambda v: self.detector.update_params(h_max=v))
        cv2.createTrackbar("S Min", self.trackbar_window, self.detector.s_min, 255, lambda v: self.detector.update_params(s_min=v))
        cv2.createTrackbar("S Max", self.trackbar_window, self.detector.s_max, 255, lambda v: self.detector.update_params(s_max=v))
        cv2.createTrackbar("V Min", self.trackbar_window, self.detector.v_min, 255, lambda v: self.detector.update_params(v_min=v))
        cv2.createTrackbar("V Max", self.trackbar_window, self.detector.v_max, 255, lambda v: self.detector.update_params(v_max=v))
        cv2.createTrackbar("Min Area", self.trackbar_window, self.detector.min_contour_area, 5000, lambda v: self.detector.update_params(min_contour_area=v))

    def _save_snapshot(self, frame: np.ndarray) -> str:
        """Saves current frame to snapshots directory."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"fire_snapshot_{timestamp}.jpg"
        filepath = os.path.join(self.snapshots_dir, filename)
        cv2.imwrite(filepath, frame)
        print(f"[INFO] Snapshot saved to: {filepath}")
        return filepath

    def run(self) -> None:
        """Starts the capture and detection loop."""
        # Convert source if digit string
        if isinstance(self.source, str) and self.source.isdigit():
            self.source = int(self.source)

        print(f"[INFO] Opening video source: {self.source}")
        self.cap = cv2.VideoCapture(self.source)

        if not self.cap.isOpened():
            print(f"[ERROR] Failed to open video source: {self.source}")
            print("[HINT] If using a webcam, ensure camera permissions are granted or try --source 1")
            return

        # Attempt setting standard resolution (640x480 or 1280x720)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        cv2.namedWindow(self.window_title, cv2.WINDOW_NORMAL)
        self.is_running = True

        print("\n=== Real-Time Fire Detection Started ===")
        print("Controls:")
        print("  [q / ESC] : Quit application")
        print("  [d]       : Toggle Debug Split View (Mask vs Original)")
        print("  [t]       : Toggle Calibration Trackbars")
        print("  [s]       : Save Snapshot")
        print("  [m]       : Toggle Audio Alarm (Mute / Unmute)")
        print("  [SPACE]   : Pause / Resume (Video Files)")
        print("=========================================\n")

        prev_time = time.time()
        fps = 0.0
        fps_alpha = 0.9  # Smoothing factor for FPS

        while self.is_running:
            if not self.is_paused:
                ret, frame = self.cap.read()
                if not ret:
                    # If reading a video file, loop back to beginning
                    if isinstance(self.source, str):
                        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    else:
                        print("[WARNING] Frame capture returned empty, retrying...")
                        time.sleep(0.1)
                        continue

                # Compute frame rate
                curr_time = time.time()
                elapsed = curr_time - prev_time
                prev_time = curr_time
                if elapsed > 0:
                    current_fps = 1.0 / elapsed
                    fps = fps_alpha * fps + (1.0 - fps_alpha) * current_fps

                # Run fire detector
                is_fire, detections, mask = self.detector.detect(frame)

                # Audio Alert
                if is_fire and self.enable_audio:
                    trigger_audio_alert()

                # Render Annotations & Bounding Boxes
                display_frame = draw_fire_boxes(
                    frame=frame,
                    detections=detections,
                    is_fire_detected=is_fire,
                    fps=fps,
                )

                # Debug Mode View
                if self.show_debug:
                    display_frame = create_side_by_side_view(display_frame, mask)

            # Display frame in OpenCV Window
            cv2.imshow(self.window_title, display_frame)

            # Keyboard Events
            key = cv2.waitKey(1) & 0xFF
            if key in (ord('q'), 27):  # 'q' or ESC
                print("[INFO] Exiting application...")
                break
            elif key == ord('d'):
                self.show_debug = not self.show_debug
                print(f"[INFO] Debug View: {'ON' if self.show_debug else 'OFF'}")
            elif key == ord('t'):
                self.show_trackbars = not self.show_trackbars
                if self.show_trackbars:
                    self._init_trackbars()
                    print("[INFO] Trackbar calibration window opened.")
                else:
                    cv2.destroyWindow(self.trackbar_window)
                    print("[INFO] Trackbar calibration window closed.")
            elif key == ord('s'):
                self._save_snapshot(display_frame)
            elif key == ord('m'):
                self.enable_audio = not self.enable_audio
                print(f"[INFO] Audio Alarm: {'ENABLED' if self.enable_audio else 'MUTED'}")
            elif key == ord(' '):
                self.is_paused = not self.is_paused
                print(f"[INFO] {'PAUSED' if self.is_paused else 'RESUMED'}")

        # Cleanup
        self.cleanup()

    def cleanup(self) -> None:
        """Release resources and destroy windows."""
        self.is_running = False
        if self.cap is not None:
            self.cap.release()
        cv2.destroyAllWindows()
        print("[INFO] Resources released successfully.")
