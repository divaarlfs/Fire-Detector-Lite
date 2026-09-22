"""
Helper script to generate a sample video with simulated fire flames for testing.
"""

import math
import random
import cv2
import numpy as np


def generate_sample_fire_video(output_path: str = "sample_fire.mp4", duration_sec: int = 6, fps: int = 30):
    width, height = 640, 480
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    total_frames = duration_sec * fps
    print(f"[INFO] Generating simulated fire video: {output_path} ({total_frames} frames)...")

    for frame_idx in range(total_frames):
        # Dark room background
        frame = np.full((height, width, 3), (25, 20, 18), dtype=np.uint8)

        # Draw fireplace / table base
        cv2.rectangle(frame, (180, 360), (460, 440), (45, 40, 35), -1)
        cv2.rectangle(frame, (170, 350), (470, 365), (60, 55, 50), -1)

        # Simulate fire appearing after frame 30
        if frame_idx >= 30:
            center_x, center_y = 320, 340
            flicker_h = int(120 + 25 * math.sin(frame_idx * 0.4) + random.randint(-10, 10))
            flicker_w = int(70 + 15 * math.cos(frame_idx * 0.3) + random.randint(-5, 5))

            # Outer Red Flame Layer
            flame_outer = np.array([
                [center_x - flicker_w, center_y],
                [center_x - flicker_w // 2, center_y - flicker_h // 2],
                [center_x + random.randint(-8, 8), center_y - flicker_h],
                [center_x + flicker_w // 2, center_y - flicker_h // 2],
                [center_x + flicker_w, center_y],
            ], dtype=np.int32)
            cv2.fillPoly(frame, [flame_outer], (10, 50, 240))  # Vibrant Red (BGR)

            # Inner Orange/Yellow Core Flame
            core_h = int(flicker_h * 0.7)
            core_w = int(flicker_w * 0.6)
            flame_core = np.array([
                [center_x - core_w, center_y],
                [center_x - core_w // 2, center_y - core_h // 2],
                [center_x + random.randint(-4, 4), center_y - core_h],
                [center_x + core_w // 2, center_y - core_h // 2],
                [center_x + core_w, center_y],
            ], dtype=np.int32)
            cv2.fillPoly(frame, [flame_core], (20, 160, 255))  # Bright Orange-Yellow (BGR)

            # Center White-Yellow Hotspot
            cv2.circle(frame, (center_x, center_y - 20), int(core_w * 0.4), (100, 230, 255), -1)

        out.write(frame)

    out.release()
    print(f"[SUCCESS] Sample fire video generated at: {output_path}")


if __name__ == "__main__":
    generate_sample_fire_video()
