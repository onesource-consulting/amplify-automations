"""Simple data structures used by the plugins.

The production project uses more feature rich implementations but for the unit
tests we only need light–weight containers describing the inputs/outputs for a
step and the result of executing a step.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Any, Optional


@dataclass
class StepIO:
    """Container describing paths used by a step."""

    inputs: Dict[str, str]
    outputs: Dict[str, str]


@dataclass
class ValidationResult:
    """Represents the outcome of running a step."""

    success: bool
    messages: List[str]
    metrics: Optional[Dict[str, Any]] = None
