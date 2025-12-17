"""
Word Counter - Count words, lines, and characters in text files.

A simple text analysis tool similar to the Unix 'wc' command.
"""

import argparse
import sys
from pathlib import Path
from typing import TextIO, NamedTuple


class Stats(NamedTuple):
    """Statistics for a text."""
    lines: int
    words: int
    chars: int
    bytes: int


def count_text(text: str) -> Stats:
    """
    Count statistics for a text string.
    
    Args:
        text: The text to analyze
    
    Returns:
        Stats namedtuple with lines, words, chars, bytes
    """
    lines = text.count('\n')
    # Add 1 if text doesn't end with newline but has content
    if text and not text.endswith('\n'):
        lines += 1
    
    words = len(text.split())
    chars = len(text)
    byte_count = len(text.encode('utf-8'))
    
    return Stats(lines=lines, words=words, chars=chars, bytes=byte_count)


def count_file(filepath: str) -> Stats:
    """
    Count statistics for a file.
    
    Args:
        filepath: Path to the file
    
    Returns:
        Stats namedtuple
    
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    
    text = path.read_text(encoding='utf-8')
    return count_text(text)


def count_stdin() -> Stats:
    """Count statistics from stdin."""
    text = sys.stdin.read()
    return count_text(text)


def format_stats(stats: Stats, filename: str = "", show_lines: bool = True,
                 show_words: bool = True, show_chars: bool = True,
                 show_bytes: bool = False) -> str:
    """
    Format statistics for display.
    
    Args:
        stats: Stats namedtuple
        filename: Optional filename to append
        show_lines: Include line count
        show_words: Include word count
        show_chars: Include character count
        show_bytes: Include byte count
    
    Returns:
        Formatted string
    """
    parts = []
    if show_lines:
        parts.append(f"{stats.lines:8d}")
    if show_words:
        parts.append(f"{stats.words:8d}")
    if show_chars:
        parts.append(f"{stats.chars:8d}")
    if show_bytes:
        parts.append(f"{stats.bytes:8d}")
    
    result = " ".join(parts)
    if filename:
        result += f" {filename}"
    return result


def most_common_words(text: str, n: int = 10) -> list:
    """
    Find the most common words in text.
    
    Args:
        text: Text to analyze
        n: Number of words to return
    
    Returns:
        List of (word, count) tuples
    """
    words = text.lower().split()
    # Simple word cleaning
    words = [w.strip('.,!?;:"\'()[]{}') for w in words]
    words = [w for w in words if w]
    
    word_counts = {}
    for word in words:
        word_counts[word] = word_counts.get(word, 0) + 1
    
    sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
    return sorted_words[:n]


def main():
    parser = argparse.ArgumentParser(
        description="Count words, lines, and characters in files"
    )
    parser.add_argument("files", nargs="*", help="Files to analyze (stdin if none)")
    parser.add_argument("-l", "--lines", action="store_true", help="Show only line count")
    parser.add_argument("-w", "--words", action="store_true", help="Show only word count")
    parser.add_argument("-c", "--chars", action="store_true", help="Show only character count")
    parser.add_argument("-b", "--bytes", action="store_true", help="Show byte count")
    parser.add_argument("--top", type=int, metavar="N", help="Show top N most common words")
    
    args = parser.parse_args()
    
    # If no specific flag, show all (except bytes)
    show_all = not (args.lines or args.words or args.chars or args.bytes)
    show_lines = args.lines or show_all
    show_words = args.words or show_all
    show_chars = args.chars or show_all
    show_bytes = args.bytes
    
    total = Stats(0, 0, 0, 0)
    
    if not args.files:
        # Read from stdin
        stats = count_stdin()
        print(format_stats(stats, "", show_lines, show_words, show_chars, show_bytes))
    else:
        for filepath in args.files:
            try:
                stats = count_file(filepath)
                print(format_stats(stats, filepath, show_lines, show_words, show_chars, show_bytes))
                total = Stats(
                    total.lines + stats.lines,
                    total.words + stats.words,
                    total.chars + stats.chars,
                    total.bytes + stats.bytes
                )
                
                if args.top:
                    text = Path(filepath).read_text()
                    common = most_common_words(text, args.top)
                    print(f"\nTop {args.top} words in {filepath}:")
                    for word, count in common:
                        print(f"  {word}: {count}")
                    
            except FileNotFoundError as e:
                print(f"Error: {e}", file=sys.stderr)
        
        if len(args.files) > 1:
            print(format_stats(total, "total", show_lines, show_words, show_chars, show_bytes))


if __name__ == "__main__":
    main()

