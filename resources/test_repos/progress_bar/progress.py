"""
Progress Bar - Display progress bars for iterables and long-running operations.

A simple progress bar implementation for tracking iteration progress in the terminal.
"""

import sys
import time
from typing import Iterable, Optional, TypeVar

T = TypeVar('T')


class ProgressBar:
    """A simple terminal progress bar."""
    
    def __init__(
        self,
        iterable: Optional[Iterable[T]] = None,
        total: Optional[int] = None,
        desc: str = "",
        width: int = 40,
        fill_char: str = "█",
        empty_char: str = "░"
    ):
        """
        Initialize a progress bar.
        
        Args:
            iterable: Optional iterable to wrap
            total: Total number of iterations (inferred from iterable if not provided)
            desc: Description prefix for the progress bar
            width: Width of the progress bar in characters
            fill_char: Character for completed portion
            empty_char: Character for remaining portion
        """
        self.iterable = iterable
        self.total = total or (len(iterable) if hasattr(iterable, '__len__') else None)
        self.desc = desc
        self.width = width
        self.fill_char = fill_char
        self.empty_char = empty_char
        self.current = 0
        self.start_time = None
    
    def __iter__(self):
        """Iterate with progress updates."""
        self.start_time = time.time()
        for item in self.iterable:
            yield item
            self.current += 1
            self._display()
        self._finish()
    
    def _display(self):
        """Display the current progress bar state."""
        if self.total:
            percent = self.current / self.total
            filled = int(self.width * percent)
            bar = self.fill_char * filled + self.empty_char * (self.width - filled)
            
            elapsed = time.time() - self.start_time
            rate = self.current / elapsed if elapsed > 0 else 0
            
            prefix = f"{self.desc}: " if self.desc else ""
            sys.stdout.write(f"\r{prefix}|{bar}| {self.current}/{self.total} [{elapsed:.1f}s, {rate:.1f}it/s]")
            sys.stdout.flush()
    
    def _finish(self):
        """Complete the progress bar."""
        sys.stdout.write("\n")
        sys.stdout.flush()
    
    def update(self, n: int = 1):
        """Manually update progress by n steps."""
        self.current += n
        self._display()


def progress(iterable: Iterable[T], desc: str = "", total: Optional[int] = None) -> Iterable[T]:
    """
    Wrap an iterable with a progress bar.
    
    Args:
        iterable: The iterable to wrap
        desc: Description to show before the progress bar
        total: Total count (optional, inferred if possible)
    
    Returns:
        An iterator that displays progress as it iterates
    
    Example:
        for item in progress(range(100), desc="Processing"):
            process(item)
    """
    return ProgressBar(iterable, total=total, desc=desc)


def main():
    """Demo the progress bar functionality."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Progress bar demo")
    parser.add_argument("-n", "--count", type=int, default=50, help="Number of iterations")
    parser.add_argument("-d", "--delay", type=float, default=0.05, help="Delay between iterations")
    parser.add_argument("--desc", default="Processing", help="Progress bar description")
    
    args = parser.parse_args()
    
    print(f"Running progress bar demo with {args.count} iterations...")
    
    for i in progress(range(args.count), desc=args.desc):
        time.sleep(args.delay)
    
    print("Done!")


if __name__ == "__main__":
    main()

