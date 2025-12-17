"""
Password Generator - Generate secure random passwords.

A simple command-line tool for creating strong passwords with customizable options.
"""

import random
import string
import argparse


def generate_password(
    length: int = 16,
    use_uppercase: bool = True,
    use_lowercase: bool = True,
    use_digits: bool = True,
    use_special: bool = True,
    exclude_chars: str = ""
) -> str:
    """
    Generate a random password with specified characteristics.
    
    Args:
        length: Length of the password (default: 16)
        use_uppercase: Include uppercase letters (default: True)
        use_lowercase: Include lowercase letters (default: True)
        use_digits: Include digits (default: True)
        use_special: Include special characters (default: True)
        exclude_chars: Characters to exclude from password
    
    Returns:
        A randomly generated password string
    
    Raises:
        ValueError: If no character types are selected or length < 1
    """
    if length < 1:
        raise ValueError("Password length must be at least 1")
    
    chars = ""
    if use_uppercase:
        chars += string.ascii_uppercase
    if use_lowercase:
        chars += string.ascii_lowercase
    if use_digits:
        chars += string.digits
    if use_special:
        chars += string.punctuation
    
    if not chars:
        raise ValueError("At least one character type must be selected")
    
    # Remove excluded characters
    for char in exclude_chars:
        chars = chars.replace(char, "")
    
    if not chars:
        raise ValueError("No characters available after exclusions")
    
    return ''.join(random.choice(chars) for _ in range(length))


def generate_multiple(count: int, **kwargs) -> list:
    """Generate multiple passwords with the same settings."""
    return [generate_password(**kwargs) for _ in range(count)]


def check_strength(password: str) -> dict:
    """
    Check the strength of a password.
    
    Returns a dict with strength score and feedback.
    """
    score = 0
    feedback = []
    
    if len(password) >= 8:
        score += 1
    else:
        feedback.append("Password should be at least 8 characters")
    
    if len(password) >= 12:
        score += 1
    
    if len(password) >= 16:
        score += 1
    
    if any(c.isupper() for c in password):
        score += 1
    else:
        feedback.append("Add uppercase letters")
    
    if any(c.islower() for c in password):
        score += 1
    else:
        feedback.append("Add lowercase letters")
    
    if any(c.isdigit() for c in password):
        score += 1
    else:
        feedback.append("Add digits")
    
    if any(c in string.punctuation for c in password):
        score += 1
    else:
        feedback.append("Add special characters")
    
    strength = "weak"
    if score >= 5:
        strength = "medium"
    if score >= 7:
        strength = "strong"
    
    return {
        "score": score,
        "max_score": 7,
        "strength": strength,
        "feedback": feedback
    }


def main():
    parser = argparse.ArgumentParser(description="Generate secure random passwords")
    parser.add_argument("-l", "--length", type=int, default=16, help="Password length (default: 16)")
    parser.add_argument("-c", "--count", type=int, default=1, help="Number of passwords to generate")
    parser.add_argument("--no-upper", action="store_true", help="Exclude uppercase letters")
    parser.add_argument("--no-lower", action="store_true", help="Exclude lowercase letters")
    parser.add_argument("--no-digits", action="store_true", help="Exclude digits")
    parser.add_argument("--no-special", action="store_true", help="Exclude special characters")
    parser.add_argument("-e", "--exclude", default="", help="Characters to exclude")
    parser.add_argument("--check", metavar="PASSWORD", help="Check strength of a password")
    
    args = parser.parse_args()
    
    if args.check:
        result = check_strength(args.check)
        print(f"Strength: {result['strength']} ({result['score']}/{result['max_score']})")
        if result['feedback']:
            print("Suggestions:")
            for tip in result['feedback']:
                print(f"  - {tip}")
        return
    
    passwords = generate_multiple(
        args.count,
        length=args.length,
        use_uppercase=not args.no_upper,
        use_lowercase=not args.no_lower,
        use_digits=not args.no_digits,
        use_special=not args.no_special,
        exclude_chars=args.exclude
    )
    
    for pwd in passwords:
        print(pwd)


if __name__ == "__main__":
    main()

