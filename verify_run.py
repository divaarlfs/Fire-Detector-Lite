"""
End-to-end verification script for Fire Detection pipeline.
"""

import os
import sys
import cv2

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.detector import FireDetector
from src.utils import draw_fire_boxes, create_side_by_side_view


def verify_pipeline():
    video_path = "sample_fire.mp4"
    if not os.path.exists(video_path):
        print(f"[ERROR] {video_path} not found.")
        sys.exit(1)

    cap = cv2.VideoCapture(video_path)
    detector = FireDetector()
    os.makedirs("snapshots", exist_ok=True)

    found_fire = False
    frame_count = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frame_count += 1
        is_fire, detections, mask = detector.detect(frame)

        if is_fire and not found_fire:
            found_fire = True
            annotated = draw_fire_boxes(frame, detections, is_fire, fps=30.0)
            split_view = create_side_by_side_view(annotated, mask)
            snapshot_path = os.path.join("snapshots", "verification_snapshot.jpg")
            cv2.imwrite(snapshot_path, split_view)
            conf = detections[0]["confidence"]
            print(f"[SUCCESS] Fire detected at frame {frame_count}!")
            print(f"          - Detections count: {len(detections)}")
            print(f"          - Bounding Box: {detections[0]['bbox']}")
            print(f"          - Confidence: {conf * 100:.1f}%")
            print(f"          - Verification Snapshot saved to: {snapshot_path}")
            break

    cap.release()

    if not found_fire:
        print("[FAILED] Fire was not detected in sample video.")
        sys.exit(1)
    else:
        print("\n[PASSED] All pipeline verification checks succeeded!")


if __name__ == "__main__":
    verify_pipeline()
