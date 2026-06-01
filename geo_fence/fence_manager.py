"""
Geo-Fence Manager
-----------------
Validates that an attendance scan originates from the campus network.

Strategy:
  1. Check client IP against configured allowed prefixes (campus LAN ranges).
  2. Loopback (127.x) and private ranges used by campus Wi-Fi are whitelisted.
  3. Any external/unknown IP is rejected with GeoFenceViolation.
"""

import socket
import math
from config.settings import ALLOWED_IP_PREFIXES, COLLEGE_LAT, COLLEGE_LNG, GEOFENCE_RADIUS_METERS
from utils.exceptions import GeoFenceViolation


def get_local_ip() -> str:
    """Return the machine's outbound LAN IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def is_allowed_ip(ip: str) -> bool:
    """
    Return True if *ip* matches any configured campus IP prefix.
    Examples of allowed prefixes: '192.168.1.', '10.0.0.', '127.0.0.1'
    """
    for prefix in ALLOWED_IP_PREFIXES:
        if ip.startswith(prefix):
            return True
    return False


def validate_location(ip: str | None = None) -> str:
    """
    Validate the given (or auto-detected) IP address.
    Returns the IP string if allowed.
    Raises GeoFenceViolation if outside campus.
    """
    client_ip = ip or get_local_ip()
    if not is_allowed_ip(client_ip):
        raise GeoFenceViolation(
            f"Access denied: IP {client_ip} is outside the campus network. "
            "Attendance can only be marked on campus."
        )
    return client_ip


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in meters between two GPS coordinates."""
    R = 6371000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def validate_gps_location(lat: float, lng: float) -> float:
    """
    Validate that the coordinate is within GEOFENCE_RADIUS_METERS of the college.
    Returns distance in meters.
    Raises GeoFenceViolation if outside radius.
    """
    if COLLEGE_LAT is None or COLLEGE_LNG is None:
        return 0.0
    
    distance = haversine_distance(lat, lng, COLLEGE_LAT, COLLEGE_LNG)
    if distance > GEOFENCE_RADIUS_METERS:
        raise GeoFenceViolation(
            f"Access denied: You are too far from the campus ({distance:.1f}m). "
            f"Attendance can only be marked within {GEOFENCE_RADIUS_METERS:.0f}m of campus."
        )
    return distance
