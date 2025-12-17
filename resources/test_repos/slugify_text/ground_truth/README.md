# Text Slugify

A Python utility for converting text strings into URL-friendly slugs. Perfect for generating clean URLs, file names, or identifiers from user input.

## Features

- Convert any text to URL-safe slugs
- Unicode normalization (handles accented characters)
- Customizable word separator
- Optional case preservation
- Maximum length limiting

## Prerequisites

- Python 3.6 or higher
- No external dependencies (uses only standard library)

## Installation

No installation required! This script uses only Python standard library modules:
- `re` - Regular expressions
- `unicodedata` - Unicode character database
- `argparse` - Command-line argument parsing

Simply download `slugify.py` and run it.

## Usage

### Basic Usage

Convert text to a slug:

```bash
python slugify.py "Hello World!"
```

Output:
```
hello-world
```

### Custom Separator

Use underscores instead of hyphens:

```bash
python slugify.py "My Blog Post Title" -s "_"
```

Output:
```
my_blog_post_title
```

### Preserve Case

Keep the original capitalization:

```bash
python slugify.py "Hello World" --no-lowercase
```

Output:
```
Hello-World
```

### Limit Length

Restrict the slug to a maximum length:

```bash
python slugify.py "This is a very long title that needs to be shortened" -m 20
```

Output:
```
this-is-a-very-long
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `text` | Input text to slugify (required) | - |
| `-s, --separator` | Word separator character | `-` |
| `--no-lowercase` | Keep original case | False |
| `-m, --max-length` | Maximum slug length (0 = no limit) | 0 |

## API Usage

Use as a Python module:

```python
from slugify import slugify

# Basic usage
slug = slugify("Hello World!")
print(slug)  # Output: hello-world

# With options
slug = slugify("Café & Restaurant", separator="_", max_length=15)
print(slug)  # Output: cafe_restaurant
```

## Examples

| Input | Output |
|-------|--------|
| `"Hello World!"` | `hello-world` |
| `"Café Münchën"` | `cafe-munchen` |
| `"100% Pure & Natural"` | `100-pure-natural` |
| `"   Extra   Spaces   "` | `extra-spaces` |

## How It Works

1. **Unicode Normalization**: Converts accented characters to ASCII equivalents
2. **Case Conversion**: Optionally converts to lowercase
3. **Character Filtering**: Removes special characters except alphanumerics
4. **Separator Replacement**: Replaces spaces with the chosen separator
5. **Length Trimming**: Optionally trims to maximum length

## Author

Inspired by python-slugify project.

