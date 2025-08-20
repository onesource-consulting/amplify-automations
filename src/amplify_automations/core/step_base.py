"""Base class for pipeline steps.

This abstract base class standardises how steps declare their inputs/outputs
and execute work, while remaining lightweight for unit tests.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from .contracts import StepIO, ValidationResult


class Step(ABC):
    """Abstract base class for all processing steps.

    Concrete steps must implement:
      - plan_io(): declare logical input/output file paths
      - run(): perform the step and return a ValidationResult
    """

    name: str = "BaseStep"

    def __init__(self, cfg: Dict[str, Any], folders: Dict[str, str], naming: Dict[str, str], period: str) -> None:
        # Store lightweight context/config so plugins and tests can operate.
        self.cfg = cfg
        self.folders = folders
        self.naming = naming
        self.period = period

    # Required API -------------------------------------------------------

    @abstractmethod
    def plan_io(self) -> StepIO:
        """Return the logical input and output paths for this step."""
        raise NotImplementedError

    @abstractmethod
    def run(self, io: StepIO) -> ValidationResult:
        """Execute the step and return a ValidationResult."""
        raise NotImplementedError

    # Optional hooks -----------------------------------------------------

    def before(self, io: StepIO) -> None:
        """Hook executed before run(). Override to add logging, prep, etc."""
        pass

    def after(self, io: StepIO, vr: ValidationResult) -> None:
        """Hook executed after run(). Override to add cleanup/metrics."""
        pass