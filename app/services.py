import re
import secrets
import string
from urllib.parse import urlparse

MAX_URL_LENGTH = 2048
SHORT_CODE_LENGTH = 6
SHORT_CODE_CHARS = string.ascii_letters + string.digits  # a-zA-Z0-9
MIN_CUSTOM_CODE_LENGTH = 4
MAX_CUSTOM_CODE_LENGTH = 10


# Let's also make sure our URL is resilient against potential race conditions.
def generate_short_code(length: int = SHORT_CODE_LENGTH) -> str:
    """Generate a random Base62 short code."""
    return "".join(secrets.choice(SHORT_CODE_CHARS) for _ in range(length))


def validate_url(url: str | None) -> tuple[bool, str]:
    """Validate a URL for shortening."""

    if not url:
        return False, "URL is required"

    if not isinstance(url, str):
        return False, "URL must be a string"

    url = url.strip()

    if len(url) > MAX_URL_LENGTH:
        return False, f"URL exceeds maximum length of {MAX_URL_LENGTH} characters"

    # Must have http:// or https://
    if not url.startswith(("http://", "https://")):
        return False, "URL must start with http:// or https://"

    # Parse and validate
    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            return False, "Invalid URL format"
        if "." not in parsed.netloc and "localhost" not in parsed.netloc.lower():
            return False, "Invalid URL format"
    except Exception:
        return False, "Invalid URL format"

    return True, ""


def validate_custom_code(code: str | None) -> tuple[bool, str]:
    """Validate a custom short code."""
    if code is None:
        return True, ""  # Custom code is optional

    if not isinstance(code, str):
        return False, "Short code must be a string"

    code = code.strip()

    if len(code) < MIN_CUSTOM_CODE_LENGTH:
        return False, f"Short code must be at least {MIN_CUSTOM_CODE_LENGTH} characters"

    if len(code) > MAX_CUSTOM_CODE_LENGTH:
        return (
            False,
            f"Short code must be less than {MAX_CUSTOM_CODE_LENGTH} characters",
        )

    # Only alphanumeric
    if not re.match(r"^[a-zA-Z0-9]+$", code):
        return False, "Short code must contain only letters and numbers"

    return True, ""
