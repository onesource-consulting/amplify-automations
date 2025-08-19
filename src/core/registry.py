"""Utilities for registering and retrieving steps."""

from typing import Dict, Type

from core.step_base import Step

# Global registry mapping step names to their classes.
_REGISTRY: Dict[str, Type[Step]] = {}


def register(name: str):
    """Decorator used to register a :class:`Step` implementation."""

    def _wrap(cls):
        _REGISTRY[name] = cls
        return cls

    return _wrap


def get_step(name: str) -> Type[Step]:
    """Retrieve a previously registered step class by name."""

    return _REGISTRY[name]

