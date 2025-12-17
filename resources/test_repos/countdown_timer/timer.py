"""
Countdown Timer - A simple terminal countdown timer.

Display a countdown timer in the terminal with optional sound notification.
"""

import time
import sys
import argparse


def parse_time(time_str: str) -> int:
    """
    Parse a time string into seconds.
    
    Formats supported:
        - "30" or "30s" -> 30 seconds
        - "5m" -> 5 minutes (300 seconds)
        - "1h" -> 1 hour (3600 seconds)
        - "1h30m" -> 1 hour 30 minutes
        - "1:30" -> 1 minute 30 seconds
        - "1:30:00" -> 1 hour 30 minutes
    
    Args:
        time_str: Time string to parse
    
    Returns:
        Total seconds as integer
    
    Raises:
        ValueError: If format is invalid
    """
    time_str = time_str.strip().lower()
    
    # Handle colon format (MM:SS or HH:MM:SS)
    if ":" in time_str:
        parts = time_str.split(":")
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        else:
            raise ValueError(f"Invalid time format: {time_str}")
    
    # Handle suffix format (1h30m20s)
    total = 0
    current = ""
    
    for char in time_str:
        if char.isdigit():
            current += char
        elif char == "h":
            total += int(current) * 3600
            current = ""
        elif char == "m":
            total += int(current) * 60
            current = ""
        elif char == "s":
            total += int(current)
            current = ""
        else:
            raise ValueError(f"Invalid character in time: {char}")
    
    # Handle remaining digits (assume seconds if no suffix)
    if current:
        total += int(current)
    
    return total


def format_time(seconds: int) -> str:
    """Format seconds as HH:MM:SS or MM:SS."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def countdown(seconds: int, message: str = "Time's up!", beep: bool = True) -> None:
    """
    Run a countdown timer.
    
    Args:
        seconds: Number of seconds to count down
        message: Message to display when done
        beep: Whether to beep when done
    """
    if seconds <= 0:
        raise ValueError("Countdown must be positive")
    
    try:
        while seconds > 0:
            time_display = format_time(seconds)
            sys.stdout.write(f"\r{time_display} ")
            sys.stdout.flush()
            time.sleep(1)
            seconds -= 1
        
        sys.stdout.write(f"\r{format_time(0)} \n")
        print(message)
        
        if beep:
            # Terminal bell
            print("\a", end="")
            
    except KeyboardInterrupt:
        print("\nTimer cancelled.")


def stopwatch() -> None:
    """Run a stopwatch (count up from 0)."""
    seconds = 0
    print("Stopwatch started. Press Ctrl+C to stop.")
    
    try:
        while True:
            time_display = format_time(seconds)
            sys.stdout.write(f"\r{time_display} ")
            sys.stdout.flush()
            time.sleep(1)
            seconds += 1
    except KeyboardInterrupt:
        print(f"\nStopped at {format_time(seconds)}")


def main():
    parser = argparse.ArgumentParser(description="Terminal countdown timer")
    parser.add_argument("time", nargs="?", help="Time to count down (e.g., 30s, 5m, 1h30m, 1:30)")
    parser.add_argument("-m", "--message", default="Time's up!", help="Message when done")
    parser.add_argument("--no-beep", action="store_true", help="Disable beep when done")
    parser.add_argument("-s", "--stopwatch", action="store_true", help="Run as stopwatch instead")
    
    args = parser.parse_args()
    
    if args.stopwatch:
        stopwatch()
    elif args.time:
        seconds = parse_time(args.time)
        print(f"Starting countdown: {format_time(seconds)}")
        countdown(seconds, args.message, beep=not args.no_beep)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

