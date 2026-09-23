import os
import urllib.request
import sys

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
os.makedirs(MODEL_DIR, exist_ok=True)

MODEL_PATH = os.path.join(MODEL_DIR, "yolov8_fire.onnx")

# HuggingFace repository providing trained YOLOv8 fire detection ONNX model
MODEL_URLS = [
    "https://huggingface.co/aryantyagiase/yolov8-fire-smoke-detection/resolve/main/best.onnx",
    "https://github.com/imnuman/fire-detection-yolo/releases/download/v1.0.0/fire_detection_yolov8n.onnx"
]

def download_model():
    if os.path.exists(MODEL_PATH) and os.path.getsize(MODEL_PATH) > 1000000:
        print(f"[MODEL] Model already exists at: {MODEL_PATH} ({os.path.getsize(MODEL_PATH)/1024/1024:.2f} MB)")
        return True

    print(f"[MODEL] Downloading YOLOv8 Fire Detection ONNX model to {MODEL_PATH}...")
    for url in MODEL_URLS:
        try:
            print(f"[MODEL] Trying download from: {url}")
            opener = urllib.request.build_opener()
            opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')]
            urllib.request.install_opener(opener)
            
            def reporthook(count, block_size, total_size):
                if total_size > 0:
                    percent = int(count * block_size * 100 / total_size)
                    sys.stdout.write(f"\rDownloading: {percent}% ({count * block_size / 1024 / 1024:.1f} MB / {total_size / 1024 / 1024:.1f} MB)")
                    sys.stdout.flush()

            urllib.request.urlretrieve(url, MODEL_PATH, reporthook=reporthook)
            print()
            if os.path.exists(MODEL_PATH) and os.path.getsize(MODEL_PATH) > 1000000:
                print(f"[MODEL] Download successful! File size: {os.path.getsize(MODEL_PATH)/1024/1024:.2f} MB")
                return True
        except Exception as e:
            print(f"\n[MODEL] Download failed from {url}: {e}")
            if os.path.exists(MODEL_PATH):
                try:
                    os.remove(MODEL_PATH)
                except Exception:
                    pass

    return False

if __name__ == "__main__":
    success = download_model()
    if not success:
        sys.exit(1)
