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
