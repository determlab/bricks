"""Date / Time bricks — 10 bricks using stdlib datetime and zoneinfo."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from bricks.core.brick import brick


@brick(tags=["date", "parsing"], category="date_time", destructive=False)
def parse_date(date_str: str, fmt: str) -> dict[str, str]:
    """Parse a date string with a format, return ISO 8601 date. Returns {result: iso_date}.

    Args:
        date_str: Date string to parse.
        fmt: strptime format (e.g. ``"%d/%m/%Y"``).

    Returns:
        dict with key ``result`` containing the ISO 8601 date string (YYYY-MM-DD).
    """
    dt = datetime.strptime(date_str, fmt)
    return {"result": dt.date().isoformat()}


@brick(tags=["date", "formatting"], category="date_time", destructive=False)
def format_date(iso_date: str, fmt: str) -> dict[str, str]:
    """Format an ISO 8601 date string with strftime format. Returns {result: formatted}.

    Args:
        iso_date: ISO 8601 date string (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS).
        fmt: strftime format string (e.g. ``"%d %B %Y"``).

    Returns:
        dict with key ``result`` containing the formatted date string.
    """
    for pattern in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(iso_date, pattern)
            return {"result": dt.strftime(fmt)}
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date {iso_date!r}")


@brick(tags=["date", "diff", "math"], category="date_time", destructive=False)
def date_diff(date_a: str, date_b: str) -> dict[str, int]:
    """Return the number of days between two ISO 8601 dates (a - b). Returns {result: days}.

    Args:
        date_a: First ISO date (YYYY-MM-DD).
        date_b: Second ISO date (YYYY-MM-DD).

    Returns:
        dict with key ``result`` containing the signed difference in days.
    """
    a = datetime.strptime(date_a, "%Y-%m-%d").date()
    b = datetime.strptime(date_b, "%Y-%m-%d").date()
    return {"result": (a - b).days}


@brick(tags=["date", "arithmetic"], category="date_time", destructive=False)
def add_days(iso_date: str, days: int) -> dict[str, str]:
    """Add a number of days to an ISO 8601 date. Returns {result: new_date}.

    Args:
        iso_date: Starting date (YYYY-MM-DD).
        days: Number of days to add (negative to subtract).

    Returns:
        dict with key ``result`` containing the resulting ISO date string.
    """
    dt = datetime.strptime(iso_date, "%Y-%m-%d").date()
    return {"result": (dt + timedelta(days=days)).isoformat()}


@brick(tags=["date", "arithmetic"], category="date_time", destructive=False)
def add_hours(iso_datetime: str, hours: int) -> dict[str, str]:
    """Add hours to an ISO 8601 datetime string. Returns {result: new_datetime}.

    Args:
        iso_datetime: Starting datetime (YYYY-MM-DDTHH:MM:SS).
        hours: Hours to add (negative to subtract).

    Returns:
        dict with key ``result`` containing the resulting ISO datetime string.
    """
    dt = datetime.strptime(iso_datetime, "%Y-%m-%dT%H:%M:%S")
    return {"result": (dt + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%S")}


@brick(tags=["date", "now", "utility"], category="date_time", destructive=False)
def now_timestamp() -> dict[str, str]:
    """Return the current UTC datetime as ISO 8601. Returns {result: timestamp}.

    Returns:
        dict with key ``result`` containing the current UTC datetime string.
    """
    return {"result": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")}


@brick(tags=["date", "timezone"], category="date_time", destructive=False)
def convert_timezone(iso_datetime: str, from_tz: str, to_tz: str) -> dict[str, str]:
    """Convert a datetime from one timezone to another. Returns {result: converted_datetime}.

    Args:
        iso_datetime: Naive datetime string (YYYY-MM-DDTHH:MM:SS).
        from_tz: Source IANA timezone (e.g. ``"UTC"``).
        to_tz: Target IANA timezone (e.g. ``"America/New_York"``).

    Returns:
        dict with key ``result`` containing the converted datetime string.
    """
    dt = datetime.strptime(iso_datetime, "%Y-%m-%dT%H:%M:%S")
    dt = dt.replace(tzinfo=ZoneInfo(from_tz))
    converted = dt.astimezone(ZoneInfo(to_tz))
    return {"result": converted.strftime("%Y-%m-%dT%H:%M:%S")}


@brick(tags=["date", "extraction", "parts"], category="date_time", destructive=False)
def extract_date_parts(iso_date: str) -> dict[str, int]:
    """Extract year, month, day, weekday from an ISO 8601 date. Returns {result: {year, month, day, weekday}}.

    Args:
        iso_date: ISO 8601 date string (YYYY-MM-DD).

    Returns:
        dict with key ``result`` containing a dict with ``year``, ``month``, ``day``,
        and ``weekday`` (0=Monday).
    """
    dt = datetime.strptime(iso_date, "%Y-%m-%d").date()
    return {"result": {"year": dt.year, "month": dt.month, "day": dt.day, "weekday": dt.weekday()}}


@brick(tags=["date", "business", "calendar"], category="date_time", destructive=False)
def is_business_day(iso_date: str) -> dict[str, bool]:
    """Check if an ISO 8601 date is a business day (Mon-Fri). Returns {result: bool}.

    Args:
        iso_date: ISO 8601 date string (YYYY-MM-DD).

    Returns:
        dict with key ``result`` — True if Monday through Friday.
    """
    dt = datetime.strptime(iso_date, "%Y-%m-%d").date()
    return {"result": dt.weekday() < 5}


@brick(tags=["date", "range", "list"], category="date_time", destructive=False)
def date_range(start: str, end: str, step_days: int = 1) -> dict[str, list[str]]:
    """Generate a list of ISO 8601 dates from start to end (exclusive). Returns {result: dates}.

    Args:
        start: Start date (YYYY-MM-DD), inclusive.
        end: End date (YYYY-MM-DD), exclusive.
        step_days: Step size in days (default 1).

    Returns:
        dict with key ``result`` containing the list of ISO date strings.
    """
    current = datetime.strptime(start, "%Y-%m-%d").date()
    stop = datetime.strptime(end, "%Y-%m-%d").date()
    dates = []
    while current < stop:
        dates.append(current.isoformat())
        current = current + timedelta(days=step_days)
    return {"result": dates}


@brick(tags=["date", "calculation"], category="date", destructive=False)
def days_until(target_date: str) -> dict[str, int]:
    """Calculate the number of days from today until a target date. Returns {result: int}.

    Args:
        target_date: Target date in ``YYYY-MM-DD`` format.

    Returns:
        dict with key ``result`` containing the number of days (negative if in the past).

    Raises:
        ValueError: If ``target_date`` is not in ``YYYY-MM-DD`` format.
    """
    target = datetime.strptime(target_date, "%Y-%m-%d").date()
    today = datetime.now(tz=timezone.utc).date()
    return {"result": (target - today).days}
