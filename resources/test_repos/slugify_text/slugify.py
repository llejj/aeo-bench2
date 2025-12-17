"""
Text Slugify - Convert text strings into URL-friendly slugs.

This script converts text with spaces, special characters, and unicode
into clean, URL-safe slug strings.
"""

import re
import unicodedata
import argparse


def slugify(text: str, separator: str = "-", lowercase: bool = True, max_length: int = 0) -> str:
    """
    Convert a text string into a URL-friendly slug.
    
    Args:
        text: The input text to convert
        separator: Character to use between words (default: "-")
        lowercase: Convert to lowercase (default: True)
        max_length: Maximum length of slug, 0 for no limit (default: 0)
    
    Returns:
        URL-friendly slug string
    """
    # Normalize unicode characters
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')
    
    # Convert to lowercase if requested
    if lowercase:
        text = text.lower()
    
    # Replace spaces and special characters with separator
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', separator, text).strip(separator)
    
    # Apply max length if specified
    if max_length > 0:
        text = text[:max_length].rstrip(separator)
    
    return text


def main():
    parser = argparse.ArgumentParser(description="Convert text to URL-friendly slugs")
    parser.add_argument("text", help="Text to convert to a slug")
    parser.add_argument("-s", "--separator", default="-", help="Word separator (default: -)")
    parser.add_argument("--no-lowercase", action="store_true", help="Keep original case")
    parser.add_argument("-m", "--max-length", type=int, default=0, help="Maximum slug length")
    
    args = parser.parse_args()
    
    slug = slugify(
        args.text,
        separator=args.separator,
        lowercase=not args.no_lowercase,
        max_length=args.max_length
    )
    
    print(slug)


if __name__ == "__main__":
    main()

