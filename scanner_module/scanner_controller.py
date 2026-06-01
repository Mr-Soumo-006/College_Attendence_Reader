"""
Scanner Controller
------------------
Opens the webcam, decodes QR codes from the live feed, then validates them.
"""

import cv2
import time
from pyzbar import pyzbar
from scanner_module.camera import Camera
from scanner_module.validator import validate_qr
from utils.exceptions import (
    QRInvalidError, QRExpiredError, CameraError, StudentNotFoundError
)


def scan_and_validate(timeout_seconds: int = 30,
                      show_preview: bool = True) -> dict:
    """
    Open webcam, scan for a QR code, and validate it.

    Returns:
        {"student": <student_dict>, "raw": <qr_string>}

    Raises:
        TimeoutError         — no QR detected within timeout
        QRInvalidError       — bad signature / malformed
        QRExpiredError       — valid but stale
        CameraError          — webcam unavailable
        StudentNotFoundError — unknown student_id in QR
    """
    deadline = time.time() + timeout_seconds

    with Camera() as cam:
        while time.time() < deadline:
            ok, frame = cam.read_frame()
            if not ok:
                continue

            if show_preview:
                cv2.putText(
                    frame,
                    "Show QR code to camera...",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2,
                )
                cv2.imshow("Smart Campus — QR Scanner", frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    raise KeyboardInterrupt("User cancelled scan.")

            barcodes = pyzbar.decode(frame)
            for bc in barcodes:
                raw = bc.data.decode("utf-8")
                student = validate_qr(raw)
                return {"student": student, "raw": raw}

    raise TimeoutError(
        f"No QR code detected within {timeout_seconds} seconds. "
        "Please try again."
    )
