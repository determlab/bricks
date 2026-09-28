"""Checks that decide whether a brick is fit to ship (#51, ops#117 CTO ruling 4).

Shared by ``bricks check-brick`` (:mod:`bricks.cli.main`) and the stdlib
contract tests (``tests/stdlib/test_contracts.py``): building a plausible
example call from a brick's signature (:func:`synthesize_inputs`), and the
four checks the ruling names — load, name clash, complete ``Meta``, and the
Mission 048 output contract (:func:`run_checks`).
"""

from __future__ import annotations

import ast
import inspect
import typing
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from bricks.core.models import BrickMeta
from bricks.core.registry import BrickRegistry
from bricks.core.schema import output_keys

_SKIP_PARAMS = frozenset({"self", "inputs", "metadata"})

# Known example inputs for bricks whose signature alone isn't enough to build
# a safe call — an ``operator`` Literal, a regex pattern that must actually
# match, a date format string, a JSON schema shape, and so on. Moved here
# from ``tests/stdlib/test_contracts.py`` (the Mission 048 contract test) so
# `bricks check-brick bricks.stdlib` exercises every stdlib brick the same
# way that test does, not a weaker generic guess.
KNOWN_EXAMPLE_INPUTS: dict[str, dict[str, Any]] = {
    # math_numeric
    "divide": {"a": 10.0, "b": 2.0},
    "modulo": {"a": 10.0, "b": 3.0},
    "percentage": {"value": 25.0, "total": 100.0},
    "clamp_value": {"value": 5.0, "minimum": 0.0, "maximum": 10.0},
    # string_processing
    "template_string_fill": {"template": "Hello {name}", "values": {"name": "World"}},
    "extract_regex_pattern": {"text": "abc123", "pattern": r"\d+"},
    "truncate_text": {"text": "hello world", "max_length": 8},
    "concatenate_strings": {"parts": ["hello", " ", "world"]},
    "split_by_delimiter": {"text": "a,b,c", "delimiter": ","},
    "parse_date_string": {"date_str": "15/01/2024", "input_format": "%d/%m/%Y"},
    "convert_case": {"text": "hello world", "case": "upper"},
    "levenshtein_distance": {"s1": "kitten", "s2": "sitting"},
    "pad_string": {"text": "hi", "width": 10},
    "replace_substring": {"text": "hello world", "old": "world", "new": "bricks"},
    "starts_ends_with": {"text": "hello world", "prefix": "hello", "suffix": "world"},
    "truncate_string": {"text": "hello world", "max_length": 8},
    # date_time
    "parse_date": {"date_str": "2024-01-15", "fmt": "%Y-%m-%d"},
    "format_date": {"iso_date": "2024-01-15", "fmt": "%d/%m/%Y"},
    "date_diff": {"date_a": "2024-01-15", "date_b": "2024-01-10"},
    "add_days": {"iso_date": "2024-01-15", "days": 5},
    "add_hours": {"iso_datetime": "2024-01-15T12:00:00", "hours": 2},
    "extract_date_parts": {"iso_date": "2024-01-15"},
    "is_business_day": {"iso_date": "2024-01-15"},
    "date_range": {"start": "2024-01-01", "end": "2024-01-05"},
    "days_until": {"target_date": "2030-01-01"},
    # date_time (timezone — may fail without tzdata)
    "convert_timezone": {
        "iso_datetime": "2024-01-15T12:00:00",
        "from_tz": "UTC",
        "to_tz": "UTC",  # Same-zone conversion avoids OS tzdata dependency
    },
    # encoding_security
    "base64_decode": {"encoded": "aGVsbG8="},  # base64("hello")
    "compute_hash": {"data": "hello", "algorithm": "sha256"},
    "random_string": {"length": 8, "charset": "alphanumeric"},
    "escape_special_chars": {"text": "hello.world", "chars": ["."]},
    "mask_string": {"text": "secret-api-key-12345"},
    # data_transformation
    "aggregate_by_key": {
        "items": [{"cat": "a", "n": 1.0}, {"cat": "a", "n": 2.0}, {"cat": "b", "n": 5.0}],
        "group_key": "cat",
        "value_field": "n",
        "operation": "sum",
    },
    "filter_dict_list": {"items": [{"k": "v"}, {"k": "x"}], "key": "k", "value": "v"},
    "validate_json_schema": {"data": {"name": "test"}, "schema": {"required": ["name"]}},
    "merge_dictionaries": {"base": {"a": 1}, "override": {"b": 2}},
    "extract_dict_field": {"data": {"key": "value"}, "field": "key"},
    "cast_data_types": {"data": {"x": "1"}, "type_map": {"x": "int"}},
    "remove_null_values": {"data": {"a": 1, "b": None}},
    "flatten_nested_dict": {"data": {"a": {"b": 1}}},
    "deduplicate_dict_list": {"items": [{"id": 1}, {"id": 1}], "key": "id"},
    "sort_dict_list": {"items": [{"k": 2}, {"k": 1}], "key": "k"},
    "rename_dict_keys": {"data": {"old": 1}, "rename_map": {"old": "new"}},
    "group_by_key": {"items": [{"cat": "a"}, {"cat": "b"}], "key": "cat"},
    "convert_to_csv_str": {"items": [{"a": 1, "b": 2}]},
    "unflatten_dict": {"data": {"a.b": 1}},
    "calculate_aggregates": {
        "items": [{"n": 1.0}, {"n": 2.0}],
        "field": "n",
        "operation": "sum",
    },
    "join_lists_on_key": {
        "left": [{"id": 1, "val": "x"}],
        "right": [{"id": 1, "extra": "y"}],
        "key": "id",
    },
    "diff_dict_objects": {"old": {"a": 1}, "new": {"a": 2}},
    "parse_xml_to_dict": {"xml_text": "<root><item>value</item></root>"},
    "mask_sensitive_data": {"data": {"password": "secret"}, "fields": ["password"]},
    "pivot_data_structure": {
        "items": [{"k": "a", "v": 1}],
        "index_key": "k",
        "value_key": "v",
    },
    "slice_dict_list": {"items": [{"x": 1}], "start": 0, "end": 1},
    "dict_to_json_str": {"data": {"key": "value"}},
    "select_dict_keys": {"data": {"a": 1, "b": 2}, "keys": ["a"]},
    "set_dict_field": {"data": {"a": 1}, "field": "b", "value": 2},
    "count_dict_list": {"items": [{"a": 1}]},
    "extract_json_from_str": {"text": '{"key": "value"}'},
    # list_operations
    "chunk_list": {"items": [1, 2, 3, 4], "size": 2},
    "flatten_list": {"nested": [[1, 2], [3, 4]]},
    "zip_lists": {"a": [1, 2], "b": [3, 4]},
    "intersect_lists": {"a": [1, 2, 3], "b": [2, 3, 4]},
    "difference_lists": {"a": [1, 2, 3], "b": [2, 3]},
    "take_first_n": {"items": [1, 2, 3], "n": 2},
    "map_values": {"items": [{"k": "v1"}], "key": "k"},
    "reduce_sum": {"values": [1.0, 2.0, 3.0]},
    "is_empty_list": {"items": []},
    # validation
    "is_in_range": {"value": 5.0, "minimum": 0.0, "maximum": 10.0},
    "matches_pattern": {"text": "hello123", "pattern": r"[a-z]+\d+"},
    "has_required_keys": {"data": {"a": 1}, "required_keys": ["a"]},
    "compare_values": {"a": 1, "b": 2, "operator": "lt"},
    # measurement
    "measure": {"name": "vout", "value": 4.98, "unit": "V", "min": 4.9, "max": 5.1},
}


@dataclass(frozen=True)
class Problem:
    """One thing wrong with a brick, and how to fix it."""

    brick: str
    check: str
    fix: str

    def as_dict(self) -> dict[str, str]:
        """The ``--json`` row shape: ``{"brick", "check", "fix"}``."""
        return {"brick": self.brick, "check": self.check, "fix": self.fix}


@dataclass
class CheckTarget:
    """One brick to check, or a reason it could not be resolved to one.

    ``callable_`` and ``meta`` are ``None`` when the named attribute exists
    but is not a valid brick (missing ``__brick_meta__``) or does not exist
    at all — ``problems`` then already holds the check-1 finding and
    :func:`run_checks` runs nothing further for it.
    """

    name: str
    callable_: Callable[..., Any] | None
    meta: BrickMeta | None
    problems: list[Problem] = field(default_factory=list)


def synthesize_inputs(callable_: Callable[..., Any], name: str | None = None) -> dict[str, Any]:
    """Build a plausible keyword-argument call for *callable_*.

    Looks *name* up in :data:`KNOWN_EXAMPLE_INPUTS` first (the curated
    examples the stdlib contract test already uses); when not found —
    every non-stdlib brick, and any stdlib brick added since this table was
    written — auto-generates one value per required parameter (no default)
    from its type hint. Generalises the auto-generation branch
    ``tests/stdlib/test_contracts.py`` used only for stdlib bricks so the
    same heuristic exercises an arbitrary given brick too.

    Args:
        callable_: A brick callable (a plain function, ``@brick``-decorated).
        name: The registered brick name, used only to look up a known
            example. Falls back to auto-generation when omitted or unknown.

    Returns:
        A keyword argument dict suitable for calling *callable_*.
    """
    if name is not None and name in KNOWN_EXAMPLE_INPUTS:
        return dict(KNOWN_EXAMPLE_INPUTS[name])

    try:
        hints = typing.get_type_hints(callable_)
    except Exception:
        hints = {}

    sig = inspect.signature(callable_)
    inputs: dict[str, Any] = {}
    for pname, param in sig.parameters.items():
        if pname in _SKIP_PARAMS or param.default is not inspect.Parameter.empty:
            continue
        hint = hints.get(pname)
        origin = getattr(hint, "__origin__", None)
        if hint is str:
            inputs[pname] = "hello"
        elif hint is float:
            inputs[pname] = 1.0
        elif hint is int:
            inputs[pname] = 1
        elif hint is bool:
            inputs[pname] = True
        elif origin is list:
            inner_args = getattr(hint, "__args__", None)
            if inner_args and inner_args[0] is float:
                inputs[pname] = [1.0, 2.0]
            elif inner_args and inner_args[0] is str:
                inputs[pname] = ["a", "b"]
            else:
                inputs[pname] = [1, 2, 3]
        elif origin is dict:
            inputs[pname] = {"key": "value"}
        else:
            inputs[pname] = "hello"
    return inputs


def _explicit_decorator_kwargs(callable_: Callable[..., Any]) -> set[str] | None:
    """Keyword argument names literally written in *callable_*'s ``@brick(...)`` call.

    Parses the source file's AST rather than trusting the values already
    stored on ``BrickMeta``, because a stored ``destructive=False`` cannot be
    told apart from the decorator's own default — the two are
    indistinguishable once stored. Returns ``None`` when the source cannot be
    found or parsed (e.g. a dynamically built function), which the caller
    treats as "not explicit".

    Args:
        callable_: A brick callable.

    Returns:
        The keyword argument names on the matching ``@brick(...)`` call, or
        ``None`` if the source could not be inspected.
    """
    target_name = getattr(callable_, "__name__", None)
    if target_name is None:
        return None
    try:
        source_file = inspect.getsourcefile(callable_)
        if source_file is None:
            return None
        tree = ast.parse(Path(source_file).read_text(encoding="utf-8"))
    except (OSError, SyntaxError, TypeError, UnicodeDecodeError):
        return None

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name != target_name:
            continue
        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call):
                continue
            dec_func = dec.func
            dec_name = dec_func.id if isinstance(dec_func, ast.Name) else getattr(dec_func, "attr", None)
            if dec_name == "brick":
                return {kw.arg for kw in dec.keywords if kw.arg is not None}
    return None


def check_name_clash(name: str, callable_: Callable[..., Any], reference_registry: BrickRegistry) -> list[Problem]:
    """Check 2: *name* does not already name a different installed brick."""
    if reference_registry.has(name):
        existing, _existing_meta = reference_registry.get(name)
        if existing is not callable_:
            return [
                Problem(
                    brick=name,
                    check="name.clash",
                    fix=f"Rename {name!r} — it already names a different installed brick (see `bricks list`).",
                )
            ]
    return []


# Cheap, conservative signals that a brick's body reaches outside the
# process — file, network, subprocess or DB I/O. False negatives are
# expected (this is a heuristic, not a sandbox); a false positive on the
# stdlib would fail DoD 2, so the list stays narrow. No stdlib brick matches
# any of these (AGENTS.md: "The stdlib bricks make no file, network or
# process calls"), so this never fires against the installed stdlib pack.
_IO_SIGNALS: tuple[str, ...] = (
    "open(",
    "requests.",
    "urllib.",
    "http.client",
    "socket.",
    "subprocess.",
    "os.system(",
    "os.remove(",
    "os.unlink(",
    ".write_text(",
    ".read_text(",
    ".write_bytes(",
    "smtplib",
    "sqlite3",
    "boto3",
    "paramiko",
)


def _brick_source(callable_: Callable[..., Any]) -> str | None:
    """The source text of *callable_*, or ``None`` when it cannot be read."""
    try:
        return inspect.getsource(callable_)
    except (OSError, TypeError):
        return None


def _looks_like_io(source: str) -> bool:
    """``True`` if *source* contains a recognisable I/O call (see :data:`_IO_SIGNALS`)."""
    return any(signal in source for signal in _IO_SIGNALS)


def check_meta(name: str, callable_: Callable[..., Any], meta: BrickMeta) -> list[Problem]:
    """Check 3: a non-empty description, ``destructive`` declared explicitly, and I3.

    I3 (docs/DECISIONS.md): *a brick that touches the outside world must be a
    declared capability; Bricks owns no I/O.* Checked here as: a brick whose
    source shows a recognisable I/O call but is not declared
    ``destructive=True`` is flagged — the tool's only way to see the
    capability is the source, since ``BrickMeta`` itself cannot distinguish
    "no I/O" from "I/O the author forgot to declare".

    ``idempotent`` is not required to be explicit: most stdlib bricks still
    rely on the decorator's own ``idempotent=True`` default, correct for all
    of them except the four G1 clock/random bricks, which now declare
    ``idempotent=False`` explicitly (#58) — but nothing forces every *other*
    brick to say so too, so requiring it here would fail DoD 2 against the
    unmodified stdlib pack for a reason unrelated to the brick actually being
    checked.
    """
    problems: list[Problem] = []
    if not meta.description.strip():
        problems.append(
            Problem(
                brick=name,
                check="meta.description",
                fix=f"Add a non-empty description= to the @brick(...) decorator for {name!r} "
                "(see src/bricks/BRICK_STYLE_GUIDE.md).",
            )
        )
    explicit = _explicit_decorator_kwargs(callable_)
    if explicit is None or "destructive" not in explicit:
        problems.append(
            Problem(
                brick=name,
                check="meta.destructive",
                fix=f"Set destructive=True or destructive=False explicitly in the @brick(...) decorator "
                f"for {name!r} — do not rely on the default.",
            )
        )
    source = _brick_source(callable_)
    if source is not None and _looks_like_io(source) and meta.destructive is not True:
        problems.append(
            Problem(
                brick=name,
                check="meta.capability",
                fix=f"{name!r} appears to touch the outside world (file, network, process or DB I/O) but is not "
                "declared destructive=True — Bricks owns no I/O (I3): declare the capability, or remove the I/O "
                "and keep the brick pure.",
            )
        )
    return problems


def check_contract(name: str, callable_: Callable[..., Any]) -> list[Problem]:
    """Check 4: runs on a synthesized example input and returns the declared output shape."""
    try:
        inputs = synthesize_inputs(callable_, name)
    except Exception as exc:
        return [
            Problem(
                brick=name,
                check="contract.inputs",
                fix=f"Could not build example inputs for {name!r} ({exc}); give its parameters plain typed "
                "annotations (str/int/float/bool/list/dict).",
            )
        ]
    try:
        result = callable_(**inputs)
    except Exception as exc:
        return [
            Problem(
                brick=name,
                check="contract.run",
                fix=f"{name!r} raised {type(exc).__name__}: {exc} on example inputs {inputs!r} — fix the brick, "
                "or give it plainer parameter types check-brick can synthesize a safe call for.",
            )
        ]
    if not isinstance(result, dict):
        return [
            Problem(
                brick=name,
                check="contract.return",
                fix=f"{name!r} must return a dict, got {type(result).__name__} — wrap the return value in a dict.",
            )
        ]
    expected = output_keys(callable_)
    if expected:
        missing = [k for k in expected if k not in result]
        if missing:
            return [
                Problem(
                    brick=name,
                    check="contract.output_keys",
                    fix=f"{name!r} is missing declared output key(s) {missing} in its return value {result!r}.",
                )
            ]
    elif "result" not in result:
        return [
            Problem(
                brick=name,
                check="contract.result_key",
                fix=f"{name!r} must return a dict containing the key 'result' (got keys {list(result)}).",
            )
        ]
    return []


def run_checks(target: CheckTarget, reference_registry: BrickRegistry) -> list[Problem]:
    """Run checks 2-4 against *target*.

    Check 1 (does *target* resolve to a declared brick at all) is decided
    before a :class:`CheckTarget` exists — a failure there is already in
    ``target.problems``, and ``callable_``/``meta`` are ``None``, so nothing
    further runs.
    """
    if target.callable_ is None or target.meta is None:
        return list(target.problems)
    problems = list(target.problems)
    problems.extend(check_name_clash(target.name, target.callable_, reference_registry))
    problems.extend(check_meta(target.name, target.callable_, target.meta))
    problems.extend(check_contract(target.name, target.callable_))
    return problems
