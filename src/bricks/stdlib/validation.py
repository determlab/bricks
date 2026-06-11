"""Validation / Checking bricks — 10 bricks."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal
from urllib.parse import urlparse

from bricks.core.brick import brick


@brick(tags=["validation", "email"], category="validation", destructive=False)
def is_email_valid(email: str) -> dict[str, bool]:
    """Check if a string is a valid email address format. Returns {result: bool}.

    Args:
        email: String to validate.

    Returns:
        dict with key ``result`` — True if email matches standard pattern.
    """
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    return {"result": bool(re.match(pattern, email.strip()))}


@brick(tags=["validation", "url"], category="validation", destructive=False)
def is_url_valid(url: str) -> dict[str, bool]:
    """Check if a string is a valid http/https URL. Returns {result: bool}.

    Args:
        url: String to validate.

    Returns:
        dict with key ``result`` — True if URL has a valid scheme and netloc.
    """
    try:
        parsed = urlparse(url.strip())
        return {"result": parsed.scheme in {"http", "https"} and bool(parsed.netloc)}
    except Exception:
        return {"result": False}


@brick(tags=["validation", "phone"], category="validation", destructive=False)
def is_phone_valid(phone: str) -> dict[str, bool]:
    """Check if a string looks like a valid E.164 or US phone number. Returns {result: bool}.

    Args:
        phone: Phone number string.

    Returns:
        dict with key ``result`` — True if the number matches basic patterns.
    """
    cleaned = re.sub(r"[\s\-().+]", "", phone)
    return {"result": bool(re.match(r"^\d{7,15}$", cleaned))}


@brick(tags=["validation", "empty"], category="validation", destructive=False)
def is_not_empty(value: Any) -> dict[str, bool]:
    """Check that a value is not None, empty string, empty list, or empty dict. Returns {result: bool}.

    Args:
        value: Any value to check.

    Returns:
        dict with key ``result`` — True if value has content.
    """
    return {"result": value is not None and value != "" and value != [] and value != {}}


@brick(tags=["validation", "range", "numeric"], category="validation", destructive=False)
def is_in_range(value: float, minimum: float, maximum: float) -> dict[str, bool]:
    """Check if a number is within [minimum, maximum] inclusive. Returns {result: bool}.

    Args:
        value: Number to check.
        minimum: Lower bound (inclusive).
        maximum: Upper bound (inclusive).

    Returns:
        dict with key ``result`` — True if minimum <= value <= maximum.
    """
    return {"result": minimum <= value <= maximum}


@brick(tags=["validation", "regex", "pattern"], category="validation", destructive=False)
def matches_pattern(text: str, pattern: str) -> dict[str, bool]:
    """Check if text fully matches a regex pattern. Returns {result: bool}.

    Args:
        text: String to test.
        pattern: Regular expression pattern.

    Returns:
        dict with key ``result`` — True if the full string matches.
    """
    return {"result": bool(re.fullmatch(pattern, text))}


@brick(tags=["validation", "keys", "dict"], category="validation", destructive=False)
def has_required_keys(data: dict[str, Any], required_keys: list[str]) -> dict[str, bool]:
    """Check that a dict contains all required keys. Returns {result: bool}.

    Args:
        data: Dictionary to validate.
        required_keys: List of keys that must be present.

    Returns:
        dict with key ``result`` — True if all required keys are present.
    """
    return {"result": all(k in data for k in required_keys)}


@brick(tags=["validation", "numeric", "string"], category="validation", destructive=False)
def is_numeric_string(text: str) -> dict[str, bool]:
    """Check if a string represents a valid number. Returns {result: bool}.

    Args:
        text: String to test.

    Returns:
        dict with key ``result`` — True if the string can be parsed as a float.
    """
    try:
        float(text.strip())
        return {"result": True}
    except ValueError:
        return {"result": False}


@brick(tags=["validation", "date", "iso"], category="validation", destructive=False)
def is_iso_date(text: str) -> dict[str, bool]:
    """Check if a string is a valid ISO 8601 date (YYYY-MM-DD). Returns {result: bool}.

    Args:
        text: String to test.

    Returns:
        dict with key ``result`` — True if parseable as YYYY-MM-DD.
    """
    try:
        datetime.strptime(text.strip(), "%Y-%m-%d")
        return {"result": True}
    except ValueError:
        return {"result": False}


@brick(tags=["validation", "comparison"], category="validation", destructive=False)
def compare_values(a: Any, b: Any, operator: Literal["eq", "ne", "lt", "le", "gt", "ge"]) -> dict[str, bool]:
    """Compare two values using an operator. Returns {result: bool}.

    Args:
        a: Left-hand value.
        b: Right-hand value.
        operator: Comparison operator: ``"eq"``, ``"ne"``, ``"lt"``, ``"le"``, ``"gt"``, ``"ge"``.

    Returns:
        dict with key ``result`` containing the comparison result.

    Raises:
        ValueError: If operator is not recognized.
    """
    ops = {
        "eq": lambda x, y: x == y,
        "ne": lambda x, y: x != y,
        "lt": lambda x, y: x < y,
        "le": lambda x, y: x <= y,
        "gt": lambda x, y: x > y,
        "ge": lambda x, y: x >= y,
    }
    if operator not in ops:
        raise ValueError(f"Unknown operator {operator!r}. Use: eq, ne, lt, le, gt, ge")
    return {"result": bool(ops[operator](a, b))}
