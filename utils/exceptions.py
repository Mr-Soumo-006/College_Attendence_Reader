"""
Custom exceptions for the Smart Campus Attendance System.
"""


class DatabaseError(Exception):
    """Raised when a database operation fails."""


class StudentNotFoundError(Exception):
    """Raised when a student_id does not exist in the database."""


class QRInvalidError(Exception):
    """Raised when a QR code payload is malformed or its HMAC is wrong."""


class QRExpiredError(Exception):
    """Raised when a QR code is valid but past its validity window."""


class FaceAuthError(Exception):
    """Raised when face enrollment or recognition fails."""


class ProxyAttemptError(Exception):
    """Raised when a live face does not match the enrolled face."""


class GeoFenceViolation(Exception):
    """Raised when an attendance attempt comes from outside the campus network."""


class CameraError(Exception):
    """Raised when the webcam cannot be opened or read."""


class MLModelError(Exception):
    """Raised when the ML model is missing or training data is insufficient."""
