"""Simple pipeline runner for Amplify Automations.

The runner loads a pipeline configuration, instantiates the registered step
classes and executes them sequentially.  A list of :class:`StepLog` entries is
returned summarising the outcome of each step.  This module intentionally keeps
dependencies light so it can operate in minimal environments.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping
import hashlib

from .core.contracts import StepLog
from .core.registry import get_step


def _hash_file(path: str) -> str:
    """Return the hex digest for ``path`` using MD5.

    Missing files yield an empty string.
    """

    try:
        h = hashlib.md5()
        with open(path, "rb") as f:  # noqa: S324 - non-security use
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except FileNotFoundError:
        return ""


def _load_config(cfg: str | Path | Mapping[str, Any]) -> Dict[str, Any]:
    """Load pipeline configuration from ``cfg``.

    ``cfg`` may be a mapping already or a path/str to a YAML file.  To avoid a
    hard dependency on PyYAML, the import is performed lazily when a YAML file
    needs to be parsed.
    """

    if isinstance(cfg, Mapping):
        return dict(cfg)

    try:
        import yaml
    except Exception as exc:  # pragma: no cover - YAML is optional
        raise ImportError("PyYAML is required to load pipeline configuration from files") from exc

    path = Path(cfg)
    data = path.read_text()
    return yaml.safe_load(data)


def run_pipeline(cfg: str | Path | Mapping[str, Any]) -> List[StepLog]:
    """Execute a configured pipeline and return logs for each step.

    Parameters
    ----------
    cfg:
        Either a mapping containing the pipeline definition or a path to a
        YAML file describing the pipeline.
    """

    config = _load_config(cfg)

    period = config.get("period", "")
    folders = config.get("folders", {})
    naming = config.get("naming", {})

    logs: List[StepLog] = []
    for item in config.get("pipeline", []):
        step_name = item["step"]
        step_cls = get_step(step_name)
        step_cfg = {k: v for k, v in item.items() if k != "step"}

        step = step_cls(step_cfg, folders, naming, period)
        io = step.plan_io()
        step.before(io)
        result = step.run(io)
        step.after(io, result)

        log = StepLog(
            step_name=step_name,
            period=period,
            status="ok" if result.ok else "error",
            messages=list(result.messages),
            metrics=dict(result.metrics),
            input_hashes={k: _hash_file(v) for k, v in io.inputs.items() if Path(v).is_file()},
            output_hashes={k: _hash_file(v) for k, v in io.outputs.items() if Path(v).is_file()},
        )
        logs.append(log)

    return logs


__all__ = ["run_pipeline"]

