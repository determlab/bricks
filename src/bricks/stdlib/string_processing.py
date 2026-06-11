"""String / Text Processing bricks — 20 bricks."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from typing import Literal

from bricks.core.brick import brick


@brick(tags=["string", "template"], category="string_processing", destructive=False)
def template_string_fill(template: str, values: dict[str, str]) -> dict[str, str]:
    """Fill a template string with {key} placeholders. Returns {result: filled}.

    Args:
        template: String with ``{key}`` placeholders.
        values: Dict mapping placeholder names to replacement values.

    Returns:
        dict with key ``result`` containing the filled string.
    """
    return {"result": template.format(**values)}


@brick(tags=["string", "regex", "extraction"], category="string_processing", destructive=False)
def extract_regex_pattern(text: str, pattern: str) -> dict[str, list[str]]:
    """Find all non-overlapping matches of a regex pattern. Returns {result: matches}.

    Args:
        text: Input string to search.
        pattern: Regular expression pattern.

    Returns:
        dict with key ``result`` containing a list of matched strings.
    """
    return {"result": re.findall(pattern, text)}


@brick(tags=["string", "cleaning"], category="string_processing", destructive=False)
def clean_whitespace(text: str) -> dict[str, str]:
    """Strip leading/trailing whitespace and collapse internal runs. Returns {result: cleaned}.

    Args:
        text: Input string.

    Returns:
        dict with key ``result`` containing the cleaned string.
    """
    return {"result": " ".join(text.split())}


@brick(tags=["string", "truncate"], category="string_processing", destructive=False)
def truncate_text(text: str, max_length: int) -> dict[str, str]:
    """Truncate text to max_length characters, appending '...' if cut. Returns {result: truncated}.

    Args:
        text: Input string.
        max_length: Maximum allowed length (including ellipsis).

    Returns:
        dict with key ``result`` containing the truncated string.
    """
    if len(text) <= max_length:
        return {"result": text}
    return {"result": text[: max(0, max_length - 3)] + "..."}


@brick(tags=["string", "join"], category="string_processing", destructive=False)
def concatenate_strings(parts: list[str], separator: str = "") -> dict[str, str]:
    """Join a list of strings with a separator. Returns {result: joined}.

    Args:
        parts: List of strings to join.
        separator: String to place between items (default empty string).

    Returns:
        dict with key ``result`` containing the joined string.
    """
    return {"result": separator.join(parts)}


@brick(tags=["string", "split"], category="string_processing", destructive=False)
def split_by_delimiter(text: str, delimiter: str) -> dict[str, list[str]]:
    """Split a string by delimiter. Returns {result: parts}.

    Args:
        text: Input string.
        delimiter: The separator string.

    Returns:
        dict with key ``result`` containing the list of parts.
    """
    return {"result": text.split(delimiter)}


@brick(tags=["string", "privacy", "redaction"], category="string_processing", destructive=False)
def redact_pii_patterns(text: str) -> dict[str, str]:
    """Redact common PII patterns (email, phone, SSN) with [REDACTED]. Returns {result: redacted}.

    Args:
        text: Input string potentially containing PII.

    Returns:
        dict with key ``result`` containing the redacted string.
    """
    # Email
    text = re.sub(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", "[REDACTED_EMAIL]", text)
    # US phone: (555) 123-4567 or 555-123-4567 or 5551234567
    text = re.sub(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "[REDACTED_PHONE]", text)
    # SSN: 123-45-6789
    text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED_SSN]", text)
    return {"result": text}


@brick(tags=["string", "date", "parsing"], category="string_processing", destructive=False)
def parse_date_string(date_str: str, input_format: str) -> dict[str, str]:
    """Parse a date string with strptime format, return ISO 8601. Returns {result: iso_date}.

    Args:
        date_str: Date string to parse.
        input_format: strptime format string (e.g. ``"%d/%m/%Y"``).

    Returns:
        dict with key ``result`` containing the ISO 8601 date string.
    """
    dt = datetime.strptime(date_str, input_format)
    return {"result": dt.date().isoformat()}


@brick(tags=["string", "url", "extraction"], category="string_processing", destructive=False)
def extract_urls(text: str) -> dict[str, list[str]]:
    """Extract all http/https URLs from text. Returns {result: urls}.

    Args:
        text: Input string.

    Returns:
        dict with key ``result`` containing a list of found URLs.
    """
    pattern = r"https?://[^\s\"'<>]+"
    return {"result": re.findall(pattern, text)}


@brick(tags=["string", "html", "cleaning"], category="string_processing", destructive=False)
def remove_html_tags(text: str) -> dict[str, str]:
    """Remove all HTML tags from a string. Returns {result: plain_text}.

    Args:
        text: String potentially containing HTML markup.

    Returns:
        dict with key ``result`` containing only the text content.
    """
    return {"result": re.sub(r"<[^>]+>", "", text)}


@brick(tags=["string", "case", "transform"], category="string_processing", destructive=False)
def convert_case(text: str, case: Literal["upper", "lower", "title", "snake", "camel"]) -> dict[str, str]:
    """Convert string case. Returns {result: converted}.

    Args:
        text: Input string.
        case: Target case: ``"upper"``, ``"lower"``, ``"title"``, ``"snake"``, ``"camel"``.

    Returns:
        dict with key ``result`` containing the converted string.

    Raises:
        ValueError: If case is not recognized.
    """
    if case == "upper":
        return {"result": text.upper()}
    if case == "lower":
        return {"result": text.lower()}
    if case == "title":
        return {"result": text.title()}
    if case == "snake":
        return {"result": re.sub(r"[\s\-]+", "_", text).lower()}
    if case == "camel":
        parts = re.split(r"[\s_\-]+", text)
        return {"result": parts[0].lower() + "".join(p.title() for p in parts[1:])}
    raise ValueError(f"Unknown case {case!r}. Use: upper, lower, title, snake, camel")


@brick(tags=["string", "email", "extraction"], category="string_processing", destructive=False)
def extract_emails(text: str) -> dict[str, list[str]]:
    """Extract all email addresses from text. Returns {result: emails}.

    Args:
        text: Input string.

    Returns:
        dict with key ``result`` containing a list of found email addresses.
    """
    pattern = r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
    return {"result": re.findall(pattern, text)}


@brick(tags=["string", "count", "stats"], category="string_processing", destructive=False)
def count_words_chars(text: str) -> dict[str, int]:
    """Count words and characters in text. Returns {result: {words: int, chars: int}}.

    Args:
        text: Input string.

    Returns:
        dict with key ``result`` containing a dict with ``words`` and ``chars`` counts.
    """
    return {"result": {"words": len(text.split()), "chars": len(text)}}


@brick(tags=["string", "cleaning", "punctuation"], category="string_processing", destructive=False)
def strip_punctuation(text: str) -> dict[str, str]:
    """Remove all punctuation characters from text. Returns {result: stripped}.

    Args:
        text: Input string.

    Returns:
        dict with key ``result`` containing text with punctuation removed.
    """
    return {"result": "".join(ch for ch in text if not unicodedata.category(ch).startswith("P"))}


@brick(tags=["string", "similarity", "distance"], category="string_processing", destructive=False)
def levenshtein_distance(s1: str, s2: str) -> dict[str, int]:
    """Compute the Levenshtein edit distance between two strings. Returns {result: distance}.

    Args:
        s1: First string.
        s2: Second string.

    Returns:
        dict with key ``result`` containing the edit distance.
    """
    m, n = len(s1), len(s2)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[:]
        dp[0] = i
        for j in range(1, n + 1):
            if s1[i - 1] == s2[j - 1]:
                dp[j] = prev[j - 1]
            else:
                dp[j] = 1 + min(prev[j], dp[j - 1], prev[j - 1])
    return {"result": dp[n]}


@brick(tags=["string", "markdown", "extraction"], category="string_processing", destructive=False)
def extract_markdown_fences(text: str) -> dict[str, str]:
    """Extract the content of the first markdown code fence. Returns {result: content}.

    Args:
        text: String potentially containing a markdown code fence.

    Returns:
        dict with key ``result`` containing the fence content, or empty string if none found.
    """
    match = re.search(r"```[^\n]*\n(.*?)```", text, re.DOTALL)
    return {"result": match.group(1) if match else ""}


@brick(tags=["string", "padding"], category="string_processing", destructive=False)
def pad_string(text: str, width: int, pad_char: str = " ") -> dict[str, str]:
    """Left-pad a string to the given width. Returns {result: padded}.

    Args:
        text: Input string.
        width: Target total width.
        pad_char: Character used for padding (default space).

    Returns:
        dict with key ``result`` containing the padded string.
    """
    return {"result": text.rjust(width, pad_char[0] if pad_char else " ")}


@brick(tags=["string", "replace"], category="string_processing", destructive=False)
def replace_substring(text: str, old: str, new: str) -> dict[str, str]:
    """Replace all occurrences of old with new in text. Returns {result: replaced}.

    Args:
        text: Input string.
        old: Substring to find.
        new: Replacement string.

    Returns:
        dict with key ``result`` containing the modified string.
    """
    return {"result": text.replace(old, new)}


@brick(tags=["string", "check", "predicate"], category="string_processing", destructive=False)
def starts_ends_with(text: str, prefix: str, suffix: str) -> dict[str, bool]:
    """Check if text starts with prefix AND ends with suffix. Returns {result: bool}.

    Args:
        text: Input string.
        prefix: Required prefix (pass empty string to skip).
        suffix: Required suffix (pass empty string to skip).

    Returns:
        dict with key ``result`` — True if both conditions hold.
    """
    starts = text.startswith(prefix) if prefix else True
    ends = text.endswith(suffix) if suffix else True
    return {"result": starts and ends}


@brick(tags=["string", "reverse"], category="string_processing", destructive=False)
def reverse_string(text: str) -> dict[str, str]:
    """Reverse a string character by character. Returns {result: reversed}.

    Args:
        text: Input string.

    Returns:
        dict with key ``result`` containing the reversed string.
    """
    return {"result": text[::-1]}


@brick(tags=["string", "truncate"], category="string", destructive=False)
def truncate_string(text: str, max_length: int, suffix: str = "...") -> dict[str, str]:
    """Truncate a string to max_length characters, appending suffix if truncated. Returns {result: str}.

    Args:
        text: Input string.
        max_length: Maximum length of the output string (including suffix).
        suffix: String appended when truncation occurs (default ``"..."``).

    Returns:
        dict with key ``result`` containing the truncated string.
    """
    if len(text) <= max_length:
        return {"result": text}
    cut = max(0, max_length - len(suffix))
    return {"result": text[:cut] + suffix}
