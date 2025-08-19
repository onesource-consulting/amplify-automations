"""Base class for steps in the demo pipeline."""

from __future__ import annotations

from typing import Any, Dict


class Step:
    """Minimal step implementation.

    Real project steps inherit from a richer base class.  The simplified version
    merely stores configuration and context information so that unit tests can
    exercise the plugin logic.
    """

    name = "Step"

    def __init__(self, cfg: Dict[str, Any], folders: Dict[str, str], naming: Dict[str, str], period: str) -> None:
        self.cfg = cfg
        self.folders = folders
        self.naming = naming
        self.period = period

    def plan_io(self):
        raise NotImplementedError

    def run(self, io):
        raise NotImplementedError
