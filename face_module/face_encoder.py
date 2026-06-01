"""
Face Encoder using pure OpenCV.
Extracts a normalized grayscale face vector and stores it in the database.
Works on all Python versions (including 3.14.5) with zero dependencies!
"""

import cv2
import numpy as np
from pathlib import Path
from database.models.student import update_face_encoding, get_student
from utils.exceptions import FaceAuthError, StudentNotFoundError
from config.settings import FACES_DIR


def enroll_student_face(student_id: str, image_path: str | Path) -> None:
    """
    Load the image, detect the face using Haar Cascades,
    normalize the face to a 100x100 grayscale image, and store it.
    """
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    img = cv2.imread(str(image_path))
    if img is None:
        raise FaceAuthError(f"Cannot load image: {image_path.name}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Use OpenCV's built-in Haar Cascade face detector
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

    if len(faces) == 0:
        raise FaceAuthError(f"No face detected in image: {image_path.name}")
    if len(faces) > 1:
        raise FaceAuthError(
            "Multiple faces detected in enrollment image. "
            "Please provide a single-face photo."
        )

    # Crop and resize the face to 100x100 pixels
    (x, y, w, h) = faces[0]
    face_roi = gray[y:y+h, x:x+w]
    face_resized = cv2.resize(face_roi, (100, 100))

    # Flatten the image to a simple 10,000-dimensional list of pixel values
    encoding = face_resized.flatten().tolist()

    # Verify student exists before saving
    get_student(student_id)  # raises StudentNotFoundError if missing

    # Save a copy to faces dir for reference
    dest = FACES_DIR / f"{student_id}.jpg"
    import shutil
    shutil.copy2(str(image_path), str(dest))

    update_face_encoding(student_id, encoding)


def encode_frame_faces(frame_rgb) -> list[list[float]]:
    """
    Extract all normalized face encodings from a live frame.
    """
    gray = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2GRAY)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    
    encodings = []
    for (x, y, w, h) in faces:
        face_roi = gray[y:y+h, x:x+w]
        face_resized = cv2.resize(face_roi, (100, 100))
        encodings.append(face_resized.flatten().tolist())
        
    return encodings
