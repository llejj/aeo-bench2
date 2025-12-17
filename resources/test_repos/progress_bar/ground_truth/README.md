# Progress Bar

A lightweight Python library for displaying progress bars in the terminal. Track the progress of loops, file operations, or any iterable with a visual progress indicator.

## Features

- Wrap any iterable with a progress bar
- Automatic iteration counting
- Elapsed time and rate display
- Customizable appearance (width, characters)
- Description prefix support
- Manual update mode for non-iterable progress

## Prerequisites

- Python 3.6 or higher
- No external dependencies (uses only standard library)

## Installation

No installation required! This script uses only Python standard library modules:
- `sys` - Terminal output
- `time` - Timing calculations
- `typing` - Type hints

Simply download `progress.py` and import it.

## Usage

### Basic Usage - Wrap an Iterable

```python
from progress import progress

# Wrap any iterable
for item in progress(range(100)):
    process(item)
```

Output:
```
|████████████████████░░░░░░░░░░░░░░░░░░░░| 50/100 [2.5s, 20.0it/s]
```

### With Description

Add a label to your progress bar:

```python
for item in progress(range(100), desc="Downloading"):
    download(item)
```

Output:
```
Downloading: |████████████████████████████████████████| 100/100 [5.0s, 20.0it/s]
```

### Custom Total Count

For iterables without known length:

```python
for item in progress(data_stream, desc="Processing", total=1000):
    process(item)
```

### Using the ProgressBar Class

For more control, use the class directly:

```python
from progress import ProgressBar

pbar = ProgressBar(my_list, desc="Working", width=50)
for item in pbar:
    do_work(item)
```

### Manual Updates

For non-iterable progress tracking:

```python
from progress import ProgressBar

pbar = ProgressBar(total=100, desc="Uploading")
for chunk in upload_chunks():
    upload(chunk)
    pbar.update(1)
```

## Command Line Demo

Run the demo to see the progress bar in action:

```bash
python progress.py
```

### Demo Options

| Option | Description | Default |
|--------|-------------|---------|
| `-n, --count` | Number of iterations | 50 |
| `-d, --delay` | Delay between iterations (seconds) | 0.05 |
| `--desc` | Progress bar description | "Processing" |

Example:
```bash
python progress.py -n 100 -d 0.02 --desc "Loading"
```

## API Reference

### `progress(iterable, desc="", total=None)`

Convenience function to wrap an iterable with a progress bar.

**Parameters:**
- `iterable`: Any iterable object
- `desc`: Optional description prefix
- `total`: Optional total count (auto-detected if possible)

**Returns:** Iterator with progress display

### `ProgressBar` Class

**Constructor Parameters:**
- `iterable`: Optional iterable to wrap
- `total`: Total iterations (required if iterable has no length)
- `desc`: Description prefix
- `width`: Bar width in characters (default: 40)
- `fill_char`: Character for filled portion (default: █)
- `empty_char`: Character for empty portion (default: ░)

**Methods:**
- `update(n=1)`: Manually increment progress by n

## Output Format

```
Description: |████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░| current/total [elapsed, rate]
```

## Author

Inspired by tqdm project.

