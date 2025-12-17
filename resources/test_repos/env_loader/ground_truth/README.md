# Environment Loader

A Python utility for loading environment variables from `.env` files. Keep your configuration separate from code and easily manage different environments.

## Features

- Parse `.env` files with KEY=value format
- Load variables into `os.environ`
- Support for quoted values (single and double quotes)
- Skip comments and empty lines
- Optional override of existing variables
- Command-line interface for inspection

## Prerequisites

- Python 3.6 or higher
- No external dependencies (uses only standard library)

## Installation

No installation required! This script uses only Python standard library modules:
- `os` - Environment variable access
- `re` - Regular expression parsing
- `argparse` - Command-line argument parsing
- `pathlib` - File path handling

Simply download `dotenv_loader.py` and use it.

## .env File Format

Create a `.env` file in your project root:

```
# Database configuration
DATABASE_URL=postgresql://localhost/mydb
DATABASE_USER=admin

# API Keys (use quotes for special characters)
API_KEY="abc123-xyz-789"
SECRET_KEY='my-secret-key'

# Feature flags
DEBUG=true
```

## Usage

### As a Python Module

```python
from dotenv_loader import load_dotenv, get_env

# Load from default .env file
load_dotenv()

# Access variables
database_url = get_env("DATABASE_URL")
api_key = get_env("API_KEY", default="no-key")

# Load from custom file
load_dotenv("config/production.env")
```

### Override Existing Variables

By default, existing environment variables are not overwritten:

```python
# Override existing variables
load_dotenv(override=True)
```

### Command Line Interface

List variables in a .env file (values masked):

```bash
python dotenv_loader.py --list
```

Output:
```
Variables in .env:
  DATABASE_URL=pos***
  API_KEY=abc***
```

Load and get a specific variable:

```bash
python dotenv_loader.py -g DATABASE_URL
```

Load from a custom file:

```bash
python dotenv_loader.py config/production.env --list
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `file` | Path to .env file | `.env` |
| `-l, --list` | List variables without loading | False |
| `-o, --override` | Override existing variables | False |
| `-g, --get KEY` | Get a specific variable | None |

## API Reference

### `load_dotenv(filepath=".env", override=False)`

Load environment variables from a file.

**Parameters:**
- `filepath`: Path to the .env file
- `override`: Whether to override existing variables

**Returns:** Dictionary of loaded variables

### `get_env(key, default=None)`

Get an environment variable with optional default.

**Parameters:**
- `key`: Variable name
- `default`: Default value if not found

**Returns:** Variable value or default

### `parse_env_file(filepath)`

Parse a .env file without loading into environment.

**Parameters:**
- `filepath`: Path to the .env file

**Returns:** Dictionary of key-value pairs

## Examples

### Basic Application Setup

```python
from dotenv_loader import load_dotenv, get_env

# Load configuration at startup
load_dotenv()

# Use in your application
config = {
    "database": get_env("DATABASE_URL"),
    "debug": get_env("DEBUG", "false").lower() == "true",
    "port": int(get_env("PORT", "8000"))
}
```

### Multiple Environment Files

```python
import sys
from dotenv_loader import load_dotenv

# Load base config first, then environment-specific
load_dotenv(".env")
load_dotenv(f".env.{sys.argv[1]}", override=True)  # e.g., .env.production
```

## Security Notes

- Never commit `.env` files to version control
- Add `.env` to your `.gitignore`
- Use different `.env` files for development and production
- The `--list` command masks values for security

## Author

Inspired by python-dotenv project.

