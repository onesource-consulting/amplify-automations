"""Minimal registry used to associate step names with their classes."""

from __future__ import annotations

from typing import Callable, Dict, Type

_REGISTRY: Dict[str, Type] = {}


def register(name: str) -> Callable[[Type], Type]:
    """Class decorator registering a step implementation."""
    def decorator(cls: Type) -> Type:
        _REGISTRY[name] = cls
        return cls
    return decorator


def get(name: str) -> Type:
    return _REGISTRY[name]
