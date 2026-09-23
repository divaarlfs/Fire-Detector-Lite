"""
Web-based Real-Time Fire Detection Dashboard with Flask and OpenCV.
Supports both Client Browser Camera (getUserMedia for Phone/Laptop) and Server VideoCapture.
"""

import os
import sys
import time
import base64
import socket
import threading
from typing import Dict, Any
import cv2
import numpy as np
from flask import Flask, Response, render_template, request, jsonify, send_from_directory

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.detector import FireDetector
from src.utils import draw_fire_boxes, create_side_by_side_view
from src.mqtt_notifier import MQTTFireNotifier

app = Flask(__name__, template_folder="templates", static_folder="static")

# Detector and shared state
detector = FireDetector()
mqtt_notifier = MQTTFireNotifier(
    broker="76.13.19.250",
    port=1883,
    topic="flamevision/fire_alert",
    enabled=True
)
lock = threading.Lock()

current_source = "client"  # 'client' (browser camera), '0', '1', or 'sample_fire.mp4'
cap: cv2.VideoCapture = None
view_mode = "annotated"  # 'annotated', 'split', 'mask', 'raw'

latest_status: Dict[str, Any] = {
    "is_fire": False,
    "fire_count": 0,
    "confidence": 0.0,
    "fps": 0.0,
    "source": "client",
    "view_mode": "annotated",
}

SNAPSHOTS_DIR = os.path.join(os.getcwd(), "snapshots")
os.makedirs(SNAPSHOTS_DIR, exist_ok=True)


def get_local_ip() -> str:
    """Returns the primary local IPv4 address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"


def init_camera(src: str):
    global cap, current_source
    with lock:
        if cap is not None and cap.isOpened():
            cap.release()
            cap = None
        current_source = src
        if src != "client":
            src_val = int(src) if src.isdigit() else src
            cap = cv2.VideoCapture(src_val)
            if isinstance(src_val, int):
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        print(f"[WEB APP] Video source set to: {src}")


def create_standby_frame(message="STANDBY / WAITING FOR CAMERA"):
    img = np.full((480, 640, 3), (20, 24, 30), dtype=np.uint8)
    cv2.rectangle(img, (20, 20), (620, 460), (45, 55, 70), 1)
    cv2.circle(img, (320, 200), 40, (60, 75, 95), 2)
    cv2.circle(img, (320, 200), 15, (60, 75, 95), -1)
    cv2.putText(img, message, (120, 280), cv2.FONT_HERSHEY_DUPLEX, 0.65, (160, 175, 195), 1, cv2.LINE_AA)
    cv2.putText(img, "Allow camera permissions in your browser", (135, 315), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 115, 135), 1, cv2.LINE_AA)
    return img


def generate_frames():
    """Generates server-side MJPEG video stream (when using Server Camera or Video File)."""
    global cap, latest_status, view_mode
    prev_time = time.time()
    fps = 0.0

    while True:
        frame = None
        with lock:
            if current_source != "client" and cap is not None and cap.isOpened():
                ret, raw_frame = cap.read()
                if ret:
                    frame = raw_frame
                else:
                    if isinstance(current_source, str) and not current_source.isdigit():
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, raw_frame = cap.read()
                        if ret:
                            frame = raw_frame

        if frame is None:
            latest_status.update({
                "is_fire": False,
                "fire_count": 0,
                "confidence": 0.0,
                "fps": 0.0,
                "source": current_source,
                "view_mode": view_mode,
            })
            standby = create_standby_frame(f"SOURCE [{current_source}] NOT ACTIVE")
            ret, buffer = cv2.imencode(".jpg", standby, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ret:
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n")
            time.sleep(0.2)
            continue

        curr_time = time.time()
        elapsed = curr_time - prev_time
        prev_time = curr_time
        if elapsed > 0:
            fps = 0.9 * fps + 0.1 * (1.0 / elapsed)

        is_fire, detections, mask = detector.detect(frame)
        conf = detections[0]["confidence"] if detections else 0.0

        # Trigger MQTT Alarm to ESP32-C3
        mqtt_notifier.publish_fire_alert(is_fire, len(detections), conf)

        latest_status.update({
            "is_fire": is_fire,
            "fire_count": len(detections),
            "confidence": round(float(conf * 100), 1),
            "fps": round(float(fps), 1),
            "source": current_source,
            "view_mode": view_mode,
        })

        if view_mode == "annotated":
            out_frame = draw_fire_boxes(frame, detections, is_fire, fps=fps)
        elif view_mode == "split":
            annotated = draw_fire_boxes(frame, detections, is_fire, fps=fps)
            out_frame = create_side_by_side_view(annotated, mask)
        elif view_mode == "mask":
            out_frame = cv2.applyColorMap(mask, cv2.COLORMAP_INFERNO)
        else:
            out_frame = frame

        ret, buffer = cv2.imencode(".jpg", out_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not ret:
            continue

        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n")


@app.route("/")
def index():
    local_ip = get_local_ip()
    return render_template("index.html", local_ip=local_ip)


@app.route("/video_feed")
def video_feed():
    return Response(generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/api/process_frame", methods=["POST"])
def process_client_frame():
    """
    Receives frame from client browser (Phone/Laptop camera) via base64,
    runs OpenCV fire detector, and returns bounding box coordinates & detection status.
    """
    try:
        payload = request.json or {}
        image_data = payload.get("image", "")
        if not image_data:
            return jsonify({"error": "No image provided"}), 400

        # Remove base64 header if present
        if "base64," in image_data:
            image_data = image_data.split("base64,")[1]

        image_bytes = base64.b64decode(image_data)
        np_arr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if frame is None:
            return jsonify({"error": "Invalid image format"}), 400

        # Run detector
        is_fire, detections, mask = detector.detect(frame)
        top_conf = detections[0]["confidence"] if detections else 0.0

        # Trigger MQTT Alarm to ESP32-C3
        mqtt_notifier.publish_fire_alert(is_fire, len(detections), top_conf)

        # Format detection bounding boxes for client-side canvas rendering
        formatted_detections = []
        for det in detections:
            x, y, w, h = det["bbox"]
            formatted_detections.append({
                "x": int(x),
                "y": int(y),
                "w": int(w),
                "h": int(h),
                "confidence": round(float(det["confidence"] * 100), 1),
                "area": float(det["area"]),
            })

        latest_status.update({
            "is_fire": is_fire,
            "fire_count": len(detections),
            "confidence": round(float(top_conf * 100), 1),
            "source": "client",
        })

        response_data = {
            "is_fire": is_fire,
            "fire_count": len(detections),
            "confidence": round(float(top_conf * 100), 1),
            "detections": formatted_detections,
            "frame_width": int(frame.shape[1]),
            "frame_height": int(frame.shape[0]),
        }

        # If client requested mask overlay
        include_mask = payload.get("include_mask", False)
        if include_mask:
            mask_color = cv2.applyColorMap(mask, cv2.COLORMAP_INFERNO)
            _, mask_buf = cv2.imencode(".jpg", mask_color, [cv2.IMWRITE_JPEG_QUALITY, 70])
            response_data["mask_b64"] = base64.b64encode(mask_buf).decode("utf-8")

        return jsonify(response_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/mqtt", methods=["GET", "POST"])
def mqtt_config():
    """Manages MQTT broker settings and returns status."""
    if request.method == "POST":
        data = request.json or {}
        broker = data.get("broker", mqtt_notifier.broker)
        port = int(data.get("port", mqtt_notifier.port))
        topic = data.get("topic", mqtt_notifier.topic)
        enabled = bool(data.get("enabled", mqtt_notifier.enabled))

        mqtt_notifier.update_config(broker=broker, port=port, topic=topic, enabled=enabled)
        return jsonify({"status": "success", "mqtt": mqtt_notifier.get_status()})

    return jsonify(mqtt_notifier.get_status())


@app.route("/api/mqtt/test", methods=["POST"])
def mqtt_test():
    """Triggers a test buzzer alarm on the ESP32-C3 via MQTT."""
    success = mqtt_notifier.publish_test_alarm()
    return jsonify({
        "status": "success" if success else "failed",
        "message": "Sinyal uji buzzer berhasil dikirim via MQTT" if success else "Gagal mengirim sinyal (Periksa koneksi MQTT Broker)"
    })


@app.route("/api/status")
def get_status():
    return jsonify(latest_status)


@app.route("/api/settings", methods=["GET", "POST"])
def settings():
    global view_mode
    if request.method == "POST":
        data = request.json or {}
        if "h_min" in data:
            detector.update_params(
                h_min=int(data.get("h_min", detector.h_min)),
                h_max=int(data.get("h_max", detector.h_max)),
                s_min=int(data.get("s_min", detector.s_min)),
                s_max=int(data.get("s_max", detector.s_max)),
                v_min=int(data.get("v_min", detector.v_min)),
                v_max=int(data.get("v_max", detector.v_max)),
                min_contour_area=int(data.get("min_contour_area", detector.min_contour_area)),
            )
        if "view_mode" in data:
            view_mode = data["view_mode"]
        return jsonify({"status": "success", "settings": get_current_settings()})
    return jsonify(get_current_settings())


def get_current_settings():
    return {
        "h_min": detector.h_min,
        "h_max": detector.h_max,
        "s_min": detector.s_min,
        "s_max": detector.s_max,
        "v_min": detector.v_min,
        "v_max": detector.v_max,
        "min_contour_area": detector.min_contour_area,
        "view_mode": view_mode,
        "source": current_source,
    }


@app.route("/api/set_source", methods=["POST"])
def set_source():
    data = request.json or {}
    src = str(data.get("source", "client"))
    init_camera(src)
    return jsonify({"status": "success", "source": current_source})


@app.route("/api/snapshot", methods=["POST"])
def take_snapshot():
    # If client passed base64 image data directly
    data = request.json or {}
    image_data = data.get("image", "")

    if image_data:
        if "base64," in image_data:
            image_data = image_data.split("base64,")[1]
        image_bytes = base64.b64decode(image_data)
        np_arr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    else:
        with lock:
            if cap is None or not cap.isOpened():
                return jsonify({"status": "error", "message": "Camera is not active"}), 400
            ret, frame = cap.read()
            if not ret:
                return jsonify({"status": "error", "message": "Failed to capture frame"}), 500

    if frame is None:
        return jsonify({"status": "error", "message": "No frame available"}), 400

    is_fire, detections, _ = detector.detect(frame)
    annotated = draw_fire_boxes(frame, detections, is_fire, fps=0.0)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"snapshot_{timestamp}.jpg"
    filepath = os.path.join(SNAPSHOTS_DIR, filename)
    cv2.imwrite(filepath, annotated)

    return jsonify({
        "status": "success",
        "filename": filename,
        "url": f"/snapshots/{filename}",
        "timestamp": timestamp,
        "is_fire": is_fire,
    })


@app.route("/api/snapshots", methods=["GET"])
def list_snapshots():
    files = []
    if os.path.exists(SNAPSHOTS_DIR):
        for f in sorted(os.listdir(SNAPSHOTS_DIR), reverse=True):
            if f.lower().endswith((".jpg", ".png", ".jpeg")):
                files.append({
                    "filename": f,
                    "url": f"/snapshots/{f}",
                })
    return jsonify(files)


@app.route("/snapshots/<filename>")
def serve_snapshot(filename):
    return send_from_directory(SNAPSHOTS_DIR, filename)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Web Dashboard for Fire Detection")
    parser.add_argument("--port", type=int, default=5000, help="Port to run web server on")
    parser.add_argument("--source", type=str, default="client", help="Initial video source ('client', '0', 'sample_fire.mp4')")
    args = parser.parse_args()

    init_camera(args.source)
    local_ip = get_local_ip()

    print(f"\n=======================================================")
    print(f"[FIRE DETECTION WEB DASHBOARD IS LIVE]")
    print(f"Local Access (Laptop/PC): http://127.0.0.1:{args.port}")
    print(f"Device Access (Phone/HP): http://{local_ip}:{args.port}")
    print(f"=======================================================\n")

    app.run(host="0.0.0.0", port=args.port, debug=False, threaded=True)
