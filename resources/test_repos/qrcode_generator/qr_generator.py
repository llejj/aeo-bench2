"""
QR Code Generator - Generate QR codes from text or URLs.

This script creates QR code images from input text using the qrcode library.
"""

import qrcode
from PIL import Image
import argparse
import sys


def generate_qr_code(data: str, output_path: str = "qrcode.png", size: int = 10, border: int = 4) -> str:
    """
    Generate a QR code image from the given data.
    
    Args:
        data: The text or URL to encode in the QR code
        output_path: Path where the QR code image will be saved
        size: Box size for each QR code module (default: 10)
        border: Border size in modules (default: 4)
    
    Returns:
        Path to the generated QR code image
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(output_path)
    
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate QR codes from text or URLs")
    parser.add_argument("data", help="Text or URL to encode in the QR code")
    parser.add_argument("-o", "--output", default="qrcode.png", help="Output file path (default: qrcode.png)")
    parser.add_argument("-s", "--size", type=int, default=10, help="Box size for QR modules (default: 10)")
    parser.add_argument("-b", "--border", type=int, default=4, help="Border size in modules (default: 4)")
    
    args = parser.parse_args()
    
    output_file = generate_qr_code(args.data, args.output, args.size, args.border)
    print(f"QR code saved to: {output_file}")


if __name__ == "__main__":
    main()

