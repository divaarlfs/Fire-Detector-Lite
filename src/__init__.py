"""
Fire Detection System with OpenCV
"""
from .detector import FireDetector
from .utils import draw_fire_boxes, trigger_audio_alert, create_side_by_side_view

__all__ = ["FireDetector", "draw_fire_boxes", "trigger_audio_alert", "create_side_by_side_view"]
