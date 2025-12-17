# Password Generator

A simple Python command-line tool for generating secure random passwords with customizable options.

## Features

- Generate passwords of any length
- Customize character types (uppercase, lowercase, digits, special)
- Exclude specific characters
- Generate multiple passwords at once
- Check password strength

## Installation

No external dependencies required. Uses only Python standard library:
- `random` - Random generation
- `string` - Character sets
- `argparse` - CLI parsing

## Usage

### Generate a Password

```bash
python password_gen.py
```

Output: A random 16-character password like `K#9mP@2xL$5nQ&8j`

### Custom Length

```bash
python password_gen.py -l 24
```

### Generate Multiple Passwords

```bash
python password_gen.py -c 5
```

### Exclude Character Types

```bash
# No special characters
python password_gen.py --no-special

# Letters and digits only
python password_gen.py --no-special

# Digits only
python password_gen.py --no-upper --no-lower --no-special
```

### Exclude Specific Characters

```bash
# Exclude ambiguous characters
python password_gen.py -e "0O1lI"
```

### Check Password Strength

```bash
python password_gen.py --check "MyPassword123"
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `-l, --length` | Password length | 16 |
| `-c, --count` | Number of passwords | 1 |
| `--no-upper` | Exclude uppercase letters | False |
| `--no-lower` | Exclude lowercase letters | False |
| `--no-digits` | Exclude digits | False |
| `--no-special` | Exclude special characters | False |
| `-e, --exclude` | Characters to exclude | "" |
| `--check` | Check password strength | - |

## API Usage

```python
from password_gen import generate_password, check_strength

# Generate a password
pwd = generate_password(length=20, use_special=False)

# Generate multiple
from password_gen import generate_multiple
passwords = generate_multiple(5, length=12)

# Check strength
result = check_strength("MyPassword123!")
print(result['strength'])  # "medium" or "strong"
```

## Password Strength Criteria

- Length >= 8: +1 point
- Length >= 12: +1 point
- Length >= 16: +1 point
- Has uppercase: +1 point
- Has lowercase: +1 point
- Has digits: +1 point
- Has special chars: +1 point

Score interpretation:
- 0-4: Weak
- 5-6: Medium
- 7: Strong

