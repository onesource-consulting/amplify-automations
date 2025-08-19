"""Base class for all processing steps."""

from abc import ABC, abstractmethod

from core.contracts import StepIO, ValidationResult, StepLog


class Step(ABC):
    """Abstract base class for pipeline steps.

    Each concrete step provides a :py:meth:`plan_io` method describing
    the inputs and outputs it expects and a :py:meth:`run` method that
    performs the actual work.
    """

    name: str = "BaseStep"

    def __init__(self, cfg: dict, folders: dict, naming: dict, period: str):
        self.cfg = cfg
        self.folders = folders
        self.naming = naming
        self.period = period

    @abstractmethod
    def plan_io(self) -> StepIO:
        """Return the logical input and output paths for this step."""
        raise NotImplementedError

    @abstractmethod
    def run(self, io: StepIO) -> ValidationResult:
        """Execute the step and return a :class:`ValidationResult`."""
        raise NotImplementedError

    # Optional hooks -----------------------------------------------------
    def before(self, io: StepIO) -> None:
        """Hook executed before :py:meth:`run`.

        Sub-classes can override this to perform preparation such as
        logging or resource allocation.
        """

    def after(self, io: StepIO, vr: ValidationResult) -> None:
        """Hook executed after :py:meth:`run`.

        Useful for clean-up or sending metrics.
        """

