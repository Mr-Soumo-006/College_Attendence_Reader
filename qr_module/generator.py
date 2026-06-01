"""
Dynamic QR Code Generator
--------------------------
Each QR code encodes a signed payload:
    STU_101|2026-04-01|09AM|<16-char HMAC>

The HMAC covers student_id + date + hour_slot + qr_seed, so:
  - Every student gets a DIFFERENT code even in the same hour.
  - Codes expire after QR_VALIDITY_MINUTES (default 60 min).
  - Screenshots from yesterday/another slot are rejected.
"""

import io
import qrcode
from PIL import Image
from database.models.student import get_student
from utils.crypto import sign
from utils.time_utils import now, time_slot, today_str
from config.settings import QR_CODES_DIR


def _build_payload(student_id: str, seed: str,
                   date: str | None = None, slot: str | None = None) -> str:
    dt  = now()
    d   = date or today_str()
    s   = slot or time_slot(dt)
    raw = f"{student_id}|{d}|{s}|{seed}"
    mac = sign(raw)
    return f"{student_id}|{d}|{s}|{mac}"


def generate_qr(student_id: str, save: bool = True) -> Image.Image:
    """
    Generate a time-bound QR code image for *student_id*.
    Optionally save as PNG to data/qr_codes/.
    Returns a PIL Image.
    """
    student = get_student(student_id)
    payload = _build_payload(student_id, student["qr_seed"])

    qr = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    if save:
        slot     = time_slot()
        filename = f"{student_id}_{today_str()}_{slot}.png"
        path     = QR_CODES_DIR / filename
        img.save(str(path))

    return img


def generate_qr_bytes(student_id: str) -> bytes:
    """Return the QR image as PNG bytes (for web / display use)."""
    img = generate_qr(student_id, save=False)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
