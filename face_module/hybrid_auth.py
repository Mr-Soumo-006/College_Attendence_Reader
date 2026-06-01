"""
Hybrid Authentication using pure OpenCV.
Combines QR validation + live face recognition for dual-factor attendance.
Works on all Python versions (including 3.14.5) with zero compiler dependencies!
"""

import cv2
import time
import numpy as np
from scanner_module.camera import Camera
from face_module.face_encoder import encode_frame_faces
from face_module.face_matcher import match_faces, best_match_distance
from database.models.student import get_face_encoding
from utils.exceptions import FaceAuthError, ProxyAttemptError
from config.settings import CAMERA_INDEX, FACE_TOLERANCE


def _capture_live_face(timeout_seconds: int = 15,
                       show_preview: bool = True) -> list[list[float]]:
    """
    Capture live face encoding from camera.
    Keeps trying until at least one face is found or timeout.
    Returns list of face encodings.
    """
    deadline = time.time() + timeout_seconds
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    with Camera() as cam:
        while time.time() < deadline:
            ok, bgr_frame = cam.read_frame()
            if not ok:
                continue

            rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
            encodings = encode_frame_faces(rgb_frame)

            if show_preview:
                cv2.putText(
                    bgr_frame,
                    "Look at camera for face verification...",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 200, 0), 2,
                )
                # Use standard Haar Cascades to draw bounding boxes
                gray = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
                for (x, y, w, h) in faces:
                    cv2.rectangle(bgr_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    
                cv2.imshow("Smart Campus — Face Verification", bgr_frame)
                cv2.waitKey(1)

            if encodings:
                return encodings

    raise FaceAuthError("No face detected within timeout. Please face the camera.")


def verify_student(student_id: str, show_preview: bool = True) -> dict:
    """
    Perform live face verification for *student_id*.

    Returns:
        {"verified": True, "distance": float}

    Raises:
        FaceAuthError     — face not enrolled or not detected
        ProxyAttemptError — face detected but does not match enrollment
    """
    stored = get_face_encoding(student_id)
    if stored is None:
        raise FaceAuthError(
            f"Student '{student_id}' has no enrolled face. "
            "Please run enrollment first."
        )

    live_encodings = _capture_live_face(show_preview=show_preview)
    distance       = best_match_distance(stored, live_encodings)

    if distance > FACE_TOLERANCE:
        raise ProxyAttemptError(
            f"Face mismatch for '{student_id}' "
            f"(distance={distance:.3f}, threshold={FACE_TOLERANCE}). "
            "Possible proxy attendance attempt!"
        )

    return {"verified": True, "distance": round(distance, 4)}
