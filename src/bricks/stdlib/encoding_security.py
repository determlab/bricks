"""Encoding / Security bricks — 10 bricks using stdlib only."""

from __future__ import annotations

import base64
import hashlib
import html
import secrets
import string
import uuid
from typing import Literal
from urllib.parse import quote, unquote

from bricks.core.brick import brick


@brick(tags=["encoding", "base64"], category="encoding_security", destructive=False)
def base64_encode(data: str) -> dict[str, str]:
    """Encode a UTF-8 string to base64. Returns {result: encoded}.

    Args:
        data: String to encode.

    Returns:
        dict with key ``result`` containing the base64-encoded string.
    """
    return {"result": base64.b64encode(data.encode()).decode()}


@brick(tags=["encoding", "base64"], category="encoding_security", destructive=False)
def base64_decode(encoded: str) -> dict[str, str]:
    """Decode a base64 string to UTF-8. Returns {result: decoded}.

    Args:
        encoded: Base64-encoded string.

    Returns:
        dict with key ``result`` containing the decoded string.
    """
    return {"result": base64.b64decode(encoded.encode()).decode()}


@brick(tags=["security", "hash", "digest"], category="encoding_security", destructive=False)
def compute_hash(data: str, algorithm: Literal["md5", "sha1", "sha256", "sha512"] = "sha256") -> dict[str, str]:
    """Compute a hash digest of a string. Returns {result: hex_digest}.

    Args:
        data: String to hash.
        algorithm: Hash algorithm name — ``"md5"``, ``"sha1"``, ``"sha256"``, ``"sha512"``.

    Returns:
        dict with key ``result`` containing the hexadecimal digest.

    Raises:
        ValueError: If the algorithm is not supported.
    """
    supported = {"md5", "sha1", "sha256", "sha512"}
    if algorithm not in supported:
        raise ValueError(f"Unsupported algorithm {algorithm!r}. Use: {', '.join(sorted(supported))}")
    h = hashlib.new(algorithm, data.encode())
    return {"result": h.hexdigest()}


@brick(tags=["encoding", "url"], category="encoding_security", destructive=False)
def url_encode(text: str) -> dict[str, str]:
    """Percent-encode a string for use in a URL. Returns {result: encoded}.

    Args:
        text: String to encode.

    Returns:
        dict with key ``result`` containing the percent-encoded string.
    """
    return {"result": quote(text, safe="")}


@brick(tags=["encoding", "url"], category="encoding_security", destructive=False)
def url_decode(encoded: str) -> dict[str, str]:
    """Decode a percent-encoded URL string. Returns {result: decoded}.

    Args:
        encoded: Percent-encoded string.

    Returns:
        dict with key ``result`` containing the decoded string.
    """
    return {"result": unquote(encoded)}


@brick(tags=["encoding", "html", "escape"], category="encoding_security", destructive=False)
def html_escape(text: str) -> dict[str, str]:
    """Escape HTML special characters. Returns {result: escaped}.

    Args:
        text: String that may contain HTML special characters.

    Returns:
        dict with key ``result`` containing the HTML-escaped string.
    """
    return {"result": html.escape(text)}


@brick(tags=["encoding", "html", "escape"], category="encoding_security", destructive=False)
def html_unescape(text: str) -> dict[str, str]:
    """Unescape HTML entities back to plain text. Returns {result: unescaped}.

    Args:
        text: String containing HTML entities.

    Returns:
        dict with key ``result`` containing the unescaped string.
    """
    return {"result": html.unescape(text)}


@brick(tags=["encoding", "escape", "string"], category="encoding_security", destructive=False)
def escape_special_chars(text: str, chars: list[str]) -> dict[str, str]:
    """Backslash-escape specified characters in a string. Returns {result: escaped}.

    Args:
        text: Input string.
        chars: List of characters to escape with a backslash.

    Returns:
        dict with key ``result`` containing the escaped string.
    """
    result = text
    for ch in chars:
        result = result.replace(ch, f"\\{ch}")
    return {"result": result}


@brick(tags=["security", "uuid", "identity"], category="encoding_security", destructive=False)
def generate_uuid() -> dict[str, str]:
    """Generate a random UUID v4. Returns {result: uuid_string}.

    Returns:
        dict with key ``result`` containing the UUID string.
    """
    return {"result": str(uuid.uuid4())}


@brick(tags=["security", "random", "token"], category="encoding_security", destructive=False)
def random_string(
    length: int,
    charset: Literal["alphanumeric", "hex", "alpha", "digits"] = "alphanumeric",
) -> dict[str, str]:
    """Generate a cryptographically secure random string. Returns {result: random_str}.

    Args:
        length: Number of characters to generate.
        charset: Character set — ``"alphanumeric"``, ``"hex"``, ``"alpha"``, ``"digits"``.

    Returns:
        dict with key ``result`` containing the random string.

    Raises:
        ValueError: If charset is not recognized or length < 1.
    """
    if length < 1:
        raise ValueError("length must be >= 1")
    charsets: dict[str, str] = {
        "alphanumeric": string.ascii_letters + string.digits,
        "hex": string.hexdigits[:16],
        "alpha": string.ascii_letters,
        "digits": string.digits,
    }
    if charset not in charsets:
        raise ValueError(f"Unknown charset {charset!r}. Use: {', '.join(sorted(charsets))}")
    alphabet = charsets[charset]
    return {"result": "".join(secrets.choice(alphabet) for _ in range(length))}


@brick(tags=["string", "security", "mask"], category="encoding", destructive=False)
def mask_string(text: str, visible_chars: int = 4, mask_char: str = "*") -> dict[str, str]:
    """Mask most characters of a string, keeping only the last N visible. Returns {result: str}.

    Useful for displaying sensitive values like API keys or card numbers without exposing them.

    Args:
        text: Input string to mask.
        visible_chars: Number of trailing characters to leave visible (default 4).
        mask_char: Character to use for masking (default ``"*"``).

    Returns:
        dict with key ``result`` containing the masked string.
    """
    if len(text) <= visible_chars:
        return {"result": mask_char * len(text)}
    masked_count = len(text) - visible_chars
    return {"result": mask_char * masked_count + text[-visible_chars:]}
