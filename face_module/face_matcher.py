"""
Face Matcher using pure OpenCV / NumPy normalized correlation.
Compares a live normalized face vector against a stored vector.
Works on all Python versions (including 3.14.5) with zero compiler dependencies!
"""

import numpy as np
from config.settings import FACE_TOLERANCE


def match_faces(stored_encoding: list[float],
                live_encodings: list[list[float]],
                tolerance: float = FACE_TOLERANCE) -> bool:
    """
    Return True if ANY encoding in *live_encodings* matches *stored_encoding*
    using normalized correlation distance (lower = stricter).
    """
    if not live_encodings:
        return False

    known = np.array(stored_encoding, dtype=np.float32)
    for live in live_encodings:
        live_np = np.array(live, dtype=np.float32)
        
        # Calculate Pearson correlation coefficient
        corr = np.corrcoef(known, live_np)[0, 1]
        if np.isnan(corr):
            corr = -1.0
            
        # Convert correlation [-1, 1] to distance [0, 2]
        distance = float(1.0 - corr)
        if distance <= tolerance:
            return True
            
    return False


def best_match_distance(stored_encoding: list[float],
                        live_encodings: list[list[float]]) -> float:
    """Return the minimum correlation-based distance between stored and all live faces."""
    if not live_encodings:
        return float("inf")
        
    known = np.array(stored_encoding, dtype=np.float32)
    distances = []
    for e in live_encodings:
        live_np = np.array(e, dtype=np.float32)
        corr = np.corrcoef(known, live_np)[0, 1]
        if np.isnan(corr):
            corr = -1.0
        distances.append(float(1.0 - corr))
        
    return min(distances)
