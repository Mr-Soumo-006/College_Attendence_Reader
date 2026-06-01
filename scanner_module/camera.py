"""
Camera wrapper for OpenCV webcam access.
"""

import cv2
from config.settings import CAMERA_INDEX
from utils.exceptions import CameraError


class Camera:
    """Context manager that opens and releases the webcam."""

    def __init__(self, index: int = CAMERA_INDEX):
        self._index = index
        self._cap: cv2.VideoCapture | None = None

    def __enter__(self) -> "Camera":
        self._cap = cv2.VideoCapture(self._index)
        if not self._cap.isOpened():
            raise CameraError(
                f"Cannot open camera at index {self._index}. "
                "Check CAMERA_INDEX in .env and ensure no other app is using the webcam."
            )
        return self

    def __exit__(self, *_):
        if self._cap:
            self._cap.release()
        cv2.destroyAllWindows()

    def read_frame(self) -> tuple[bool, object]:
        """Read one frame from the camera. Returns (success, frame)."""
        if not self._cap:
            raise CameraError("Camera is not open.")
        return self._cap.read()
