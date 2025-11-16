"""Minimal face detection helper built on OpenCV only.

The previous implementation used MediaPipe when available and fell back to a
Haar cascade otherwise. Render currently provisions Python 3.13, which does not
have MediaPipe wheels, so relying on MediaPipe prevents deployment. This module
now focuses on OpenCV-based detection exclusively while preserving the same
public API (`detect_faces_from_base64`) used by the Flask route.
"""

from __future__ import annotations

import base64
import binascii
import threading
from typing import Dict, List

import cv2
from cv2 import data as cv2_data
import numpy as np

_HAAR_CLASSIFIER: cv2.CascadeClassifier | None = None
_HAAR_LOCK = threading.Lock()


def _get_haar_detector() -> cv2.CascadeClassifier:
    """Lazily create a shared Haar cascade detector instance."""

    global _HAAR_CLASSIFIER
    with _HAAR_LOCK:
        if _HAAR_CLASSIFIER is None:
            cascade_path = cv2_data.haarcascades + "haarcascade_frontalface_default.xml"
            classifier = cv2.CascadeClassifier(cascade_path)
            if classifier.empty():
                raise RuntimeError(
                    "Unable to load Haar cascade for face detection."
                    " Ensure opencv-data files are available."
                )
            _HAAR_CLASSIFIER = classifier
        return _HAAR_CLASSIFIER


def _decode_image(payload: str) -> np.ndarray:
    """Decode a data URL or raw base64 string into an OpenCV BGR image."""

    if not payload:
        raise ValueError("Image data is required")

    base64_data = payload.split(",", 1)[-1]

    try:
        image_bytes = base64.b64decode(base64_data, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Invalid base64 image data") from exc

    frame_array = np.frombuffer(image_bytes, dtype=np.uint8)
    frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("Unable to decode image")

    return frame


def _normalise_bbox(x: int, y: int, w: int, h: int, width: int, height: int) -> Dict[str, float]:
    return {
        "xmin": max(0.0, x / float(width)),
        "ymin": max(0.0, y / float(height)),
        "width": max(0.0, w / float(width)),
        "height": max(0.0, h / float(height)),
    }


def detect_faces_from_base64(image_b64: str) -> Dict[str, object]:
    """Detect faces in a base64 encoded frame using OpenCV Haar cascades."""

    frame = _decode_image(image_b64)
    height, width = frame.shape[:2]

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    detector = _get_haar_detector()

    detections: List[tuple[int, int, int, int]] = detector.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=6,
        minSize=(60, 60),
    )

    faces = [
        {
            "confidence": None,
            "bbox": _normalise_bbox(x, y, w, h, width, height),
        }
        for x, y, w, h in detections
    ]

    return {
        "count": len(faces),
        "faces": faces,
        "image_size": {"width": int(width), "height": int(height)},
    }


def run_camera_face_demo(camera_index: int = 0) -> None:
    """Simple webcam loop useful for local testing."""

    capture = cv2.VideoCapture(camera_index)
    if not capture.isOpened():
        raise RuntimeError(f"Unable to open camera index {camera_index}")

    detector = _get_haar_detector()

    try:
        while True:
            ret, frame = capture.read()
            if not ret:
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            detections = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=6, minSize=(60, 60))
            for (x, y, w, h) in detections:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (30, 200, 140), 2)

            cv2.imshow("NongPlaToo Face Detection", frame)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
    finally:
        capture.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    run_camera_face_demo()
