"""Pluggy hook spec for Bricks execution lifecycle events.

Callers (composer, healer chain, engine, showcase engines) fire hooks
through a ``pluggy.PluginManager``. When no plugins are registered the
calls are no-ops — production paths pay no runtime cost.

Consumers that want live progress (e.g. the Playground SSE endpoint)
register a plugin that implements any subset of these hooks. The
PluginManager dispatches each call to every registered implementation.

Namespace is ``"bricks"``; hooks are grouped into two logical families:

- **compose/execute lifecycle**: ``compose_start``, ``compose_done``,
  ``execute_start``, ``step_start``, ``step_done``, ``run_failed``.
- **healing + checking**: ``heal_attempt``, ``raw_llm_start``,
  ``raw_llm_done``, ``check_done``.

All hook method signatures use keyword arguments per pluggy convention.
"""

from __future__ import annotations

from typing import Any

import pluggy

_NAMESPACE = "bricks"
hookspec = pluggy.HookspecMarker(_NAMESPACE)
hookimpl = pluggy.HookimplMarker(_NAMESPACE)


class BricksHookSpec:
    """Declared hooks for Bricks runtime events."""

    @hookspec
    def compose_start(self, task: str) -> None:
        """Fires before the composer dispatches its first LLM call."""

    @hookspec
    def compose_done(self, dsl: str, tokens_in: int, tokens_out: int) -> None:
        """Fires after the composer has a validated DSL response."""

    @hookspec
    def execute_start(self, blueprint_yaml: str) -> None:
        """Fires after compose succeeds, before the engine runs the first step."""

    @hookspec
    def step_start(self, step_name: str, brick_name: str) -> None:
        """Fires immediately before a brick step is invoked by the engine."""

    @hookspec
    def step_done(self, step_name: str, brick_name: str, duration_ms: int) -> None:
        """Fires immediately after a brick step returns successfully."""

    @hookspec
    def heal_attempt(self, tier: int, healer_name: str, succeeded: bool) -> None:
        """Fires once per tier the HealerChain attempts."""

    @hookspec
    def raw_llm_start(self) -> None:
        """Fires before the Raw-LLM engine invokes the provider."""

    @hookspec
    def raw_llm_done(self, response: str, tokens_in: int, tokens_out: int) -> None:
        """Fires after the Raw-LLM engine returns."""

    @hookspec
    def check_done(self, key: str, expected: Any, got: Any, passed: bool) -> None:
        """Fires once per correctness-check key when comparing outputs."""

    @hookspec
    def run_failed(self, error: str) -> None:
        """Fires when the full compose→execute→heal path exhausts without success."""


def get_plugin_manager() -> pluggy.PluginManager:
    """Return a fresh PluginManager with the BricksHookSpec registered."""
    pm = pluggy.PluginManager(_NAMESPACE)
    pm.add_hookspecs(BricksHookSpec)
    return pm
