"""Utilities for registering and retrieving step implementations.

This module provides a lightweight global registry that maps a human-readable
step name to its implementation class. It is intentionally minimal and safe to
import from plugins without causing circular import issues.
"""

from __future__ import annotations

from typing import Callable, Dict, Type, TYPE_CHECKING

if TYPE_CHECKING:
    # Only imported for type checkers to avoid runtime cycles
    from .step_base import Step

# Global registry mapping step names to their classes.
_REGISTRY: Dict[str, Type["Step"]] = {}


def register(name: str) -> Callable[[Type["Step"]], Type["Step"]]:
    """Decorator to register a :class:`Step` implementation under ``name``."""

    def _wrap(cls: Type["Step"]) -> Type["Step"]:
        _REGISTRY[name] = cls
        return cls

    return _wrap


def get_step(name: str) -> Type["Step"]:
    """Retrieve a previously registered step class by name.

    Raises
    ------
    KeyError
        If ``name`` has not been registered.
    """
    try:
        return _REGISTRY[name]
    except KeyError as e:
        raise KeyError(
            f"Step '{name}' is not registered. "
            f"Registered steps: {', '.join(sorted(_REGISTRY.keys())) or '(none)'}"
        ) from e


# Back-compat alias (older code may call `get(...)`)
get = get_step
