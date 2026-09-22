"""
Entry point for Real-Time Fire Detection System.
Run with:
    python main.py
    python main.py --source 0
    python main.py --source "path/to/video.mp4"
    python main.py --debug
    python main.py --no-audio
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.app import FireDetectionApp


def main():
    parser = argparse.ArgumentParser(
        description="Real-Time Fire Detection System using Python and OpenCV."
    )
    parser.add_argument(
        "--source",
        "-s",
        default="0",
        help="Video source index (e.g. 0, 1 for webcam) or path to video file (default: '0').",
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Start with split-screen debug mask view enabled.",
    )
    parser.add_argument(
        "--no-audio",
        action="store_true",
        help="Disable audio beeping alarm on fire detection.",
    )

    args = parser.parse_args()

    app = FireDetectionApp(
        source=args.source,
        enable_audio=not args.no_audio,
        show_debug=args.debug,
    )

    try:
        app.run()
    except KeyboardInterrupt:
        print("\n[INFO] Stopped by user (KeyboardInterrupt).")
        app.cleanup()
    except Exception as e:
        print(f"\n[ERROR] An unexpected error occurred: {e}", file=sys.stderr)
        app.cleanup()


if __name__ == "__main__":
    main()
