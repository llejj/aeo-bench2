# Word Counter

A simple Python text analysis tool for counting words, lines, and characters in files. Similar to the Unix `wc` command.

## Features

- Count lines, words, and characters
- Process multiple files with totals
- Read from stdin
- Show most common words
- Byte count option

## Installation

No external dependencies. Uses only Python standard library:
- `argparse` - CLI parsing
- `sys` - stdin/stderr
- `pathlib` - File handling

## Usage

### Count a Single File

```bash
python wordcount.py document.txt
```

Output:
```
      42      350     2100 document.txt
```
(lines, words, characters)

### Count Multiple Files

```bash
python wordcount.py file1.txt file2.txt
```

Output:
```
      10      100      600 file1.txt
      32      250     1500 file2.txt
      42      350     2100 total
```

### Read from stdin

```bash
echo "hello world" | python wordcount.py
```

Or:
```bash
cat file.txt | python wordcount.py
```

### Show Specific Counts

```bash
# Lines only
python wordcount.py -l file.txt

# Words only
python wordcount.py -w file.txt

# Characters only
python wordcount.py -c file.txt

# Bytes
python wordcount.py -b file.txt
```

### Most Common Words

```bash
python wordcount.py --top 10 file.txt
```

Output:
```
      42      350     2100 file.txt

Top 10 words in file.txt:
  the: 25
  and: 18
  to: 15
  ...
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `files` | Files to analyze (stdin if none) |
| `-l, --lines` | Show only line count |
| `-w, --words` | Show only word count |
| `-c, --chars` | Show only character count |
| `-b, --bytes` | Show byte count |
| `--top N` | Show top N most common words |

## API Usage

```python
from wordcount import count_text, count_file, most_common_words

# Count a string
stats = count_text("Hello world\nThis is a test")
print(f"Lines: {stats.lines}, Words: {stats.words}")

# Count a file
stats = count_file("document.txt")
print(f"Characters: {stats.chars}")

# Find common words
text = open("document.txt").read()
common = most_common_words(text, n=5)
for word, count in common:
    print(f"{word}: {count}")
```

## Stats Object

The `count_text` and `count_file` functions return a `Stats` namedtuple:

```python
Stats(lines=10, words=100, chars=600, bytes=620)
```

- `lines`: Number of lines (newline characters + 1 if no trailing newline)
- `words`: Number of whitespace-separated words
- `chars`: Number of characters
- `bytes`: Number of UTF-8 bytes

