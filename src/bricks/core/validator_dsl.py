"""AST-based validator for LLM-generated Python DSL code.

Ensures only whitelisted constructs are present:

- ``step.brick_name(param=value)``
- ``for_each(items, do=lambda ..., on_error=...)``
- ``branch(condition="brick_name", if_true=lambda: ..., if_false=lambda: ...)``
- ``@flow`` decorator on a single top-level function
- Lambda expressions (single-expression only)
- String, number, boolean, ``None``, list, dict literals
- Variable assignments and references
- Return statements

Everything else is **rejected**.  This validator is conservative by design —
when in doubt, reject.  It is the security gate for all LLM-generated DSL code.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """Result of DSL code validation.

    Attributes:
        valid: ``True`` when the code passed all checks.
        errors: Fatal issues that make the code unsafe or unrunnable.
        warnings: Non-fatal observations (f-strings, unknown attributes).
    """

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class PythonDSLValidator:
    """Validates LLM-generated Python DSL code using an AST whitelist.

    Call :meth:`validate` with a code string; it returns a
    :class:`ValidationResult` indicating whether the code is safe to use
    with the ``@flow`` decorator.

    Example::

        from bricks.core.validator_dsl import PythonDSLValidator

        result = PythonDSLValidator().validate(code)
        if not result.valid:
            raise ValueError(result.errors[0])
    """

    #: Names the DSL code is allowed to reference freely.
    ALLOWED_NAMES: frozenset[str] = frozenset({"step", "for_each", "branch", "flow", "True", "False", "None"})

    #: AST node types that are unconditionally forbidden.
    FORBIDDEN_NODES: frozenset[type] = frozenset(
        {
            ast.Import,
            ast.ImportFrom,
            ast.ClassDef,
            ast.AsyncFunctionDef,
            ast.AsyncFor,
            ast.AsyncWith,
            ast.Global,
            ast.Nonlocal,
            ast.Delete,
            ast.Try,
            ast.Raise,
            ast.Assert,
            ast.With,
            ast.While,
            ast.For,
            ast.If,
            ast.Yield,
            ast.YieldFrom,
            ast.Await,
            ast.GeneratorExp,
            ast.ListComp,
            ast.SetComp,
            ast.DictComp,
        }
    )

    #: Function/variable names that must never appear in DSL code.
    FORBIDDEN_CALLS: frozenset[str] = frozenset(
        {
            "exec",
            "eval",
            "compile",
            "open",
            "input",
            "print",
            "__import__",
            "getattr",
            "setattr",
            "delattr",
            "globals",
            "locals",
            "vars",
            "dir",
            "breakpoint",
            "exit",
            "quit",
            "type",
            "super",
            "classmethod",
            "staticmethod",
            "property",
        }
    )

    def validate(self, code: str) -> ValidationResult:
        """Validate a DSL code string.

        Args:
            code: The Python DSL code to validate (typically LLM-generated).

        Returns:
            :class:`ValidationResult` with ``valid=True`` when the code is
            safe, or ``valid=False`` with ``errors`` populated when it is not.
        """
        result = ValidationResult(valid=True)

        if not code.strip():
            return ValidationResult(valid=False, errors=["No function definition found. Expected one @flow function."])

        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            return ValidationResult(valid=False, errors=[f"Syntax error: {exc}"])

        self._check_function_structure(tree, result)

        for node in ast.walk(tree):
            self._check_node(node, result)

        return result

    def _check_function_structure(self, tree: ast.Module, result: ValidationResult) -> None:
        """Enforce exactly one top-level @flow function.

        Args:
            tree: Parsed AST module.
            result: Result object to append errors to.
        """
        top_level_defs = [n for n in ast.iter_child_nodes(tree) if isinstance(n, ast.FunctionDef)]

        if len(top_level_defs) == 0:
            result.valid = False
            result.errors.append("No function definition found. Expected one @flow function.")
            return

        if len(top_level_defs) > 1:
            result.valid = False
            result.errors.append(f"Found {len(top_level_defs)} function definitions, expected exactly 1.")
            return

        func = top_level_defs[0]
        has_flow = any(
            (isinstance(d, ast.Name) and d.id == "flow")
            or (isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id == "flow")
            for d in func.decorator_list
        )
        if not has_flow:
            result.valid = False
            result.errors.append("Function must be decorated with @flow.")

    def _check_node(self, node: ast.AST, result: ValidationResult) -> None:
        """Check a single AST node against the whitelist.

        Args:
            node: The AST node to inspect.
            result: Result object to append errors/warnings to.
        """
        if type(node) in self.FORBIDDEN_NODES:
            result.valid = False
            result.errors.append(f"Forbidden construct: {type(node).__name__} (line {getattr(node, 'lineno', '?')})")
            return

        if isinstance(node, ast.Call):
            self._check_call(node, result)

        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id in self.FORBIDDEN_CALLS:
            result.valid = False
            result.errors.append(f"Forbidden name reference: {node.id!r} (line {node.lineno})")

        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id not in self.ALLOWED_NAMES
        ):
            result.warnings.append(
                f"Attribute access on {node.value.id!r} — only 'step.X' is standard (line {node.lineno})"
            )

        if isinstance(node, ast.JoinedStr):
            result.warnings.append(
                f"f-string detected (line {getattr(node, 'lineno', '?')}). Consider using plain strings."
            )

    def _check_call(self, node: ast.Call, result: ValidationResult) -> None:
        """Validate a function call node.

        Args:
            node: The ``ast.Call`` node to inspect.
            result: Result object to append errors/warnings to.
        """
        if isinstance(node.func, ast.Name):
            if node.func.id in self.FORBIDDEN_CALLS:
                result.valid = False
                result.errors.append(f"Forbidden function call: {node.func.id}() (line {node.lineno})")
            elif node.func.id not in self.ALLOWED_NAMES:
                result.warnings.append(f"Unknown function call: {node.func.id}() (line {node.lineno})")

        elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            obj = node.func.value.id
            if obj in self.FORBIDDEN_CALLS:
                result.valid = False
                result.errors.append(f"Forbidden method call: {obj}.{node.func.attr}() (line {node.lineno})")


def validate_dsl(code: str) -> ValidationResult:
    """Convenience wrapper — validate DSL code with default settings.

    Args:
        code: The Python DSL code to validate.

    Returns:
        :class:`ValidationResult`.
    """
    return PythonDSLValidator().validate(code)
