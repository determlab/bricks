"""Shared test fixtures for the Bricks Engine test suite."""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

import pytest

from bricks.core.brick import BrickFunction, brick
from bricks.core.models import BrickMeta
from bricks.core.registry import BrickRegistry


@pytest.fixture()
def math_registry() -> BrickRegistry:
    """Registry with real add and multiply bricks."""
    reg = BrickRegistry()

    @brick(description="Add two numbers")
    def add(a: float, b: float) -> float:
        return a + b

    @brick(description="Multiply two numbers")
    def multiply(a: float, b: float) -> float:
        return a * b

    for fn in (add, multiply):
        typed = cast(BrickFunction, fn)
        reg.register(typed.__brick_meta__.name, typed, typed.__brick_meta__)
    return reg


@pytest.fixture()
def stub_registry_factory() -> Callable[..., BrickRegistry]:
    """Factory fixture: call with brick names to get a registry with stubs."""

    def _make(*brick_names: str) -> BrickRegistry:
        reg = BrickRegistry()
        for name in brick_names:
            reg.register(name, lambda: None, BrickMeta(name=name))
        return reg

    return _make
