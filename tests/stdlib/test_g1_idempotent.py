"""G1/G11 (docs/DECISIONS.md, #58): the four stdlib bricks that read the clock
or a CSPRNG must declare ``idempotent=False`` explicitly, not rely on the
decorator's ``idempotent=True`` default.
"""

from __future__ import annotations

from bricks.stdlib import date_time, encoding_security

# The exact four G1 bricks named in the ledger: two read the clock
# (`datetime.now`, and `.date()` on it), two draw from a CSPRNG.
_G1_BRICKS = (
    date_time.now_timestamp,
    date_time.days_until,
    encoding_security.generate_uuid,
    encoding_security.random_string,
)


def test_every_g1_brick_declares_idempotent_false() -> None:
    for fn in _G1_BRICKS:
        assert fn.__brick_meta__.idempotent is False, fn.__name__
