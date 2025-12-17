"""
Environment Loader - Load environment variables from .env files.

This script reads key-value pairs from .env files and loads them
into the environment for application configuration.
"""

import os
import re
import argparse
from pathlib import Path
from typing import Dict, Optional


def parse_env_file(filepath: str) -> Dict[str, str]:
    """
    Parse a .env file and return key-value pairs.
    
    Args:
        filepath: Path to the .env file
    
    Returns:
        Dictionary of environment variable names to values
    
    Raises:
        FileNotFoundError: If the file doesn't exist
    """
    env_vars = {}
    path = Path(filepath)
    
    if not path.exists():
        raise FileNotFoundError(f"Environment file not found: {filepath}")
    
    with open(path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Parse KEY=value format
            match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)=(.*)$', line)
            if match:
                key, value = match.groups()
                
                # Remove surrounding quotes if present
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                
                env_vars[key] = value
            else:
                print(f"Warning: Skipping invalid line {line_num}: {line}")
    
    return env_vars


def load_dotenv(filepath: str = ".env", override: bool = False) -> Dict[str, str]:
    """
    Load environment variables from a .env file.
    
    Args:
        filepath: Path to the .env file (default: ".env")
        override: If True, override existing environment variables
    
    Returns:
        Dictionary of loaded variables
    """
    env_vars = parse_env_file(filepath)
    loaded = {}
    
    for key, value in env_vars.items():
        if override or key not in os.environ:
            os.environ[key] = value
            loaded[key] = value
    
    return loaded


def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get an environment variable with optional default.
    
    Args:
        key: Environment variable name
        default: Default value if not found
    
    Returns:
        The environment variable value or default
    """
    return os.environ.get(key, default)


def main():
    parser = argparse.ArgumentParser(description="Load and display environment variables from .env files")
    parser.add_argument("file", nargs="?", default=".env", help="Path to .env file (default: .env)")
    parser.add_argument("-l", "--list", action="store_true", help="List variables without loading")
    parser.add_argument("-o", "--override", action="store_true", help="Override existing variables")
    parser.add_argument("-g", "--get", metavar="KEY", help="Get a specific variable after loading")
    
    args = parser.parse_args()
    
    try:
        if args.list:
            # Just parse and display
            env_vars = parse_env_file(args.file)
            print(f"Variables in {args.file}:")
            for key, value in env_vars.items():
                # Mask sensitive values
                display_value = value[:3] + "***" if len(value) > 6 else "***"
                print(f"  {key}={display_value}")
        else:
            # Load into environment
            loaded = load_dotenv(args.file, override=args.override)
            print(f"Loaded {len(loaded)} variables from {args.file}")
            
            if args.get:
                value = get_env(args.get)
                if value:
                    print(f"{args.get}={value}")
                else:
                    print(f"{args.get} not found")
                    
    except FileNotFoundError as e:
        print(f"Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()

