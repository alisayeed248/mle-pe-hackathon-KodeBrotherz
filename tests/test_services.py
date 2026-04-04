from app.services import (
    generate_short_code,
    validate_url,
    validate_custom_code,
)

# ── generate_short_code ──────────────────────────────────────────────────────

def test_short_code_default_length():
    code = generate_short_code()
    assert len(code) == 6

def test_short_code_custom_length():
    code = generate_short_code(length=10)
    assert len(code) == 10

def test_short_code_is_alphanumeric():
    code = generate_short_code()
    assert code.isalnum()

def test_short_code_uniqueness():
    codes = {generate_short_code() for _ in range(100)}
    assert len(codes) > 1  # should not all be the same

# ── validate_url ─────────────────────────────────────────────────────────────

def test_valid_http_url():
    valid, msg = validate_url("http://example.com")
    assert valid is True
    assert msg == ""

def test_valid_https_url():
    valid, msg = validate_url("https://google.com")
    assert valid is True

def test_url_missing():
    valid, msg = validate_url(None)
    assert valid is False
    assert "required" in msg.lower()

def test_url_empty_string():
    valid, msg = validate_url("")
    assert valid is False

def test_url_no_scheme():
    valid, msg = validate_url("example.com")
    assert valid is False
    assert "http" in msg.lower()

def test_url_too_long():
    long_url = "https://example.com/" + "a" * 2048
    valid, msg = validate_url(long_url)
    assert valid is False
    assert "length" in msg.lower()

def test_url_not_a_string():
    valid, msg = validate_url(12345)
    assert valid is False

# ── validate_custom_code ─────────────────────────────────────────────────────

def test_custom_code_none_is_ok():
    valid, msg = validate_custom_code(None)
    assert valid is True

def test_custom_code_valid():
    valid, msg = validate_custom_code("abc123")
    assert valid is True

def test_custom_code_too_short():
    valid, msg = validate_custom_code("ab")
    assert valid is False
    assert "at least" in msg.lower()

def test_custom_code_too_long():
    valid, msg = validate_custom_code("a" * 11)
    assert valid is False

def test_custom_code_special_chars():
    valid, msg = validate_custom_code("abc-123")
    assert valid is False
    assert "letters and numbers" in msg.lower()

def test_custom_code_not_a_string():
    valid, msg = validate_custom_code(99999)
    assert valid is False