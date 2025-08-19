"""Core contracts used across steps.

This module defines simple dataclasses that standardise the
communication between different steps in the pipeline. They are kept
intentionally lightweight so they can be serialised or logged with
minimal effort.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


@dataclass
class StepIO:
    """Represents the planned input and output file paths for a step.

    Attributes
    ----------
    inputs: Mapping of logical input names to their file paths.
    outputs: Mapping of logical output names to their file paths.
    """
    inputs: Dict[str, str]   # logical_name -> path
    outputs: Dict[str, str]  # logical_name -> path


@dataclass
class ValidationResult:
    """Result returned after executing a step.

    `ok` indicates whether the step succeeded. `messages` contains any
    log messages generated during the step and `metrics` exposes numeric
    information which may be useful for monitoring.

    Backwards compatibility:
    - Older code may expect a `success` boolean. A read-only property is
      provided that mirrors `ok`.
    """
    ok: bool
    messages: List[str] = field(default_factory=list)
    # allow flexible metric types (counts, timings). If you prefer strict floats, change the value type.
    metrics: Dict[str, Any] = field(default_factory=dict)

    # Back-compat for branches/tests that used `success`
    @property
    def success(self) -> bool:
        return self.ok


@dataclass
class StepLog:
    """Structured record of a step execution.

    Provides a canonical format for persisting information about each
    run of a step including the hashes of its inputs and outputs.
    """
    step_name: str
    period: str
    status: str
    messages: List[str]
    metrics: Dict[str, Any]
    input_hashes: Dict[str, str]
    output_hashes: Dict[str, str]