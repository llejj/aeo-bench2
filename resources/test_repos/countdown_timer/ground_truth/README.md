# Countdown Timer

A simple Python terminal countdown timer with stopwatch mode.

## Features

- Countdown from any duration
- Multiple time format support
- Stopwatch mode
- Custom completion message
- Terminal bell notification

## Installation

No external dependencies. Uses only Python standard library:
- `time` - Sleep function
- `sys` - Terminal output
- `argparse` - CLI parsing

## Usage

### Basic Countdown

```bash
# 30 seconds
python timer.py 30

# 5 minutes
python timer.py 5m

# 1 hour
python timer.py 1h

# 1 hour 30 minutes
python timer.py 1h30m
```

### Time Format Options

| Format | Example | Meaning |
|--------|---------|---------|
| Seconds | `30` or `30s` | 30 seconds |
| Minutes | `5m` | 5 minutes |
| Hours | `1h` | 1 hour |
| Combined | `1h30m20s` | 1 hour 30 min 20 sec |
| Colon | `5:30` | 5 min 30 sec |
| Full colon | `1:30:00` | 1 hour 30 min |

### Custom Message

```bash
python timer.py 10m -m "Break time over!"
```

### Disable Beep

```bash
python timer.py 5m --no-beep
```

### Stopwatch Mode

```bash
python timer.py -s
# Press Ctrl+C to stop
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `time` | Duration to countdown | Required |
| `-m, --message` | Message when complete | "Time's up!" |
| `--no-beep` | Disable terminal bell | False |
| `-s, --stopwatch` | Run as stopwatch | False |

## API Usage

```python
from timer import countdown, stopwatch, parse_time, format_time

# Parse time strings
seconds = parse_time("5m30s")  # Returns 330

# Format seconds
display = format_time(330)  # Returns "05:30"

# Run countdown
countdown(300, message="Done!", beep=True)

# Run stopwatch (blocking)
stopwatch()
```

## Display

The timer shows remaining time in MM:SS or HH:MM:SS format:

```
05:30
```

Updates every second in place (no scrolling).

