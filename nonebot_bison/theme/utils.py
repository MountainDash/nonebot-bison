from base64 import b64encode
from io import BytesIO
from pathlib import Path

from qrcode import constants
from qrcode.image.pil import PilImage
from qrcode.main import QRCode


def convert_to_qr(data: str, **kwarg) -> bytes:
    """Convert data to QR code
    Args:
        data (str): data to be converted
    Returns:
        bytes: QR code image
    """
    qr = QRCode(
        version=1,
        error_correction=constants.ERROR_CORRECT_L,
        box_size=10,
        border=2,
        image_factory=PilImage,
    )
    qr.add_data(data)
    qr.make(fit=True)
    f = BytesIO()
    qr.make_image(**kwarg).save(f)
    return f.getvalue()


def web_embed_image(pic_data: bytes | Path | BytesIO, *, ext: str = "png"):
    """将图片数据转换为Base64编码的Data URI"""
    match pic_data:
        case bytes():
            pic_bytes = pic_data
        case Path():
            pic_bytes = Path(pic_data).read_bytes()
        case BytesIO():
            pic_bytes = pic_data.getvalue()
        case _:
            raise TypeError("pic_data must be bytes, Path or BytesIO")
    return f"data:image/{ext};base64,{b64encode(pic_bytes).decode()}"
