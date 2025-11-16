"""Minimal face detection helper using MediaPipe and OpenCV."""

from __future__ import annotations

import base64
import binascii
import importlib
import threading
from typing import Any, Dict, Optional

import cv2
from cv2 import data as cv2_data
import numpy as np

_DETECTOR = None
_DETECTOR_LOCK = threading.Lock()
_FACE_MODULE: Optional[Any] = None
_FACE_MODULE_LOCK = threading.Lock()
_DRAWING_MODULE: Optional[Any] = None
_DRAWING_MODULE_LOCK = threading.Lock()
_HAAR_CLASSIFIER: Optional[cv2.CascadeClassifier] = None
_HAAR_LOCK = threading.Lock()


def _load_face_module() -> Optional[Any]:
    """Dynamically import mediapipe face detection module if available."""
    global _FACE_MODULE
    with _FACE_MODULE_LOCK:
        if _FACE_MODULE is None:
            try:
                _FACE_MODULE = importlib.import_module('mediapipe.solutions.face_detection')
            except ModuleNotFoundError:
                _FACE_MODULE = None
        return _FACE_MODULE


def _load_drawing_utils() -> Optional[Any]:
    """Load MediaPipe drawing utilities if available."""
    global _DRAWING_MODULE
    with _DRAWING_MODULE_LOCK:
        if _DRAWING_MODULE is None:
            try:
                _DRAWING_MODULE = importlib.import_module('mediapipe.solutions.drawing_utils')
            except ModuleNotFoundError:
                _DRAWING_MODULE = None
        return _DRAWING_MODULE


def _get_detector() -> Optional[Any]:
    """Initialise and memoise MediaPipe face detector."""
    global _DETECTOR
    with _DETECTOR_LOCK:
        if _DETECTOR is None:
            face_module = _load_face_module()
            if face_module is None:
                return None
            detector_cls = getattr(face_module, 'FaceDetection')
            _DETECTOR = detector_cls(model_selection=0, min_detection_confidence=0.5)
        return _DETECTOR


def _get_haar_detector() -> cv2.CascadeClassifier:
    """Prepare OpenCV Haar cascade as a fallback."""
    global _HAAR_CLASSIFIER
    with _HAAR_LOCK:
        if _HAAR_CLASSIFIER is None:
            cascade_path = cv2_data.haarcascades + 'haarcascade_frontalface_default.xml'
            classifier = cv2.CascadeClassifier(cascade_path)
            if classifier.empty():
                raise RuntimeError('Unable to load Haar cascade for face detection')
            _HAAR_CLASSIFIER = classifier
        return _HAAR_CLASSIFIER


def detect_faces_from_base64(image_b64: str) -> Dict[str, Any]:
    """Detect faces from a base64-encoded image payload.

    The payload may be a data URL or raw base64 string. The response contains
    relative bounding boxes sized with respect to the original image.
    """
    if not image_b64:
        raise ValueError("Image data is required")

    payload = image_b64.split(",", 1)[-1]

    try:
        image_bytes = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Invalid base64 image data") from exc

    frame_array = np.frombuffer(image_bytes, dtype=np.uint8)
    frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("Unable to decode image")

    height, width = frame.shape[:2]
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    detector = _get_detector()
    faces = []

    if detector is not None:
        with _DETECTOR_LOCK:
            results = detector.process(rgb_frame)

        if results.detections:
            for detection in results.detections:
                bbox = detection.location_data.relative_bounding_box
                confidence = float(detection.score[0]) if detection.score else None
                faces.append(
                    {
                        "confidence": confidence,
                        "bbox": {
                            "xmin": max(0.0, float(bbox.xmin)),
                            "ymin": max(0.0, float(bbox.ymin)),
                            "width": max(0.0, float(bbox.width)),
                            "height": max(0.0, float(bbox.height)),
                        },
                    }
                )
    else:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        haar = _get_haar_detector()
        detections = haar.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=6, minSize=(60, 60))
        for x, y, w, h in detections:
            faces.append(
                {
                    "confidence": None,
                    "bbox": {
                        "xmin": max(0.0, x / float(width)),
                        "ymin": max(0.0, y / float(height)),
                        "width": max(0.0, w / float(width)),
                        "height": max(0.0, h / float(height)),
                    },
                }
            )

    return {
        "count": len(faces),
        "faces": faces,
        "image_size": {"width": int(width), "height": int(height)},
    }


def run_camera_face_demo(camera_index: int = 0) -> None:
    """Run a local webcam face detection loop for quick testing.

    Press "q" or Esc to exit the preview window.
    """

    face_module = _load_face_module()
    drawing_utils = _load_drawing_utils()

    capture = cv2.VideoCapture(camera_index)
    if not capture.isOpened():
        raise RuntimeError(f"Unable to open camera index {camera_index}")

    try:
        if face_module is not None and drawing_utils is not None:
            with face_module.FaceDetection(model_selection=0, min_detection_confidence=0.5) as detector:
                while True:
                    ret, frame = capture.read()
                    if not ret:
                        break

                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    results = detector.process(rgb_frame)

                    if results.detections:
                        for detection in results.detections:
                            drawing_utils.draw_detection(frame, detection)

                    cv2.imshow("NongPlaToo Face Detection", frame)
                    key = cv2.waitKey(1) & 0xFF
                    if key in (ord('q'), 27):
                        break
        else:
            haar = _get_haar_detector()
            while True:
                ret, frame = capture.read()
                if not ret:
                    break

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                detections = haar.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=6, minSize=(60, 60))
                for x, y, w, h in detections:
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (30, 200, 140), 2)

                cv2.imshow("NongPlaToo Face Detection", frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord('q'), 27):
                    break
    finally:
        capture.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    run_camera_face_demo()
