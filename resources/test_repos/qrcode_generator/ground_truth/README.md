# QR Code Generator

A simple Python command-line tool for generating QR code images from text or URLs.

## Features

- Generate QR codes from any text or URL
- Customize output size and border
- Save as PNG image file
- Easy command-line interface

## Prerequisites

- Python 3.7 or higher

## Installation

Install the required dependencies using pip:

```bash
pip install qrcode pillow
```

## Usage

### Basic Usage

Generate a QR code from text:

```bash
python qr_generator.py "Hello, World!"
```

This creates a `qrcode.png` file in the current directory.

### Custom Output File

Specify a custom output path:

```bash
python qr_generator.py "https://github.com" -o my_qrcode.png
```

### Customize Size and Border

Adjust the QR code appearance:

```bash
python qr_generator.py "My Text" --size 15 --border 2
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `data` | Text or URL to encode (required) | - |
| `-o, --output` | Output file path | qrcode.png |
| `-s, --size` | Box size for QR modules | 10 |
| `-b, --border` | Border size in modules | 4 |

## Example Output

```
$ python qr_generator.py "https://example.com" -o example.png
QR code saved to: example.png
```

## API Usage

You can also use the generator as a Python module:

```python
from qr_generator import generate_qr_code

# Generate a QR code
output_path = generate_qr_code("Hello, World!", "hello.png")
print(f"Saved to: {output_path}")
```

## Dependencies

- [qrcode](https://pypi.org/project/qrcode/) - QR code generation library
- [Pillow](https://pypi.org/project/Pillow/) - Image processing library

## Author

Derived from python-qrcode project.

