"""Shared constants for the Bricks core engine."""

from __future__ import annotations

import re

# Matches ${inputs.channel}, ${result.value}, ${some_var}
_REF_PATTERN: re.Pattern[str] = re.compile(r"\$\{([^}]+)\}")
