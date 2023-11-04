<<<<<<< HEAD
from qrcode import constants
from qrcode.main import QRCode
from qrcode.image.svg import SvgFragmentImage


def convert_to_qr(data: str) -> str:
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
        image_factory=SvgFragmentImage,
    )
    qr.add_data(data)
    qr.make(fit=True)
    return qr.make_image().to_string().decode("utf-8")
=======
from io import BytesIO
from pathlib import Path
from base64 import b64encode


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
>>>>>>> 5a3d9f3 (:bug: 嵌入bytes需要先转换为Base64)
