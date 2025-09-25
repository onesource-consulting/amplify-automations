"""Utilities for maintaining the tutorial metadata catalogue.

The catalogue stores metadata about tutorial notebooks for each automation step.
Each step has a stable random identifier along with one or more toolset
combinations, each of which references a tutorial notebook.  This module
provides a single public entry point – :func:`register_tutorial` – that updates
the catalogue and guarantees identifiers remain unique across the repository.
"""

from __future__ import annotations

import json
from collections.abc import MutableMapping
from pathlib import Path
from typing import Iterable, List, Sequence
from uuid import uuid4


DEFAULT_CATALOG_PATH = Path("notebooks/tutorial_catalog.json")


def _load_catalog(path: Path) -> List[MutableMapping[str, object]]:
    """Return the existing catalogue data.

    If the file does not exist or contains invalid JSON, an empty list is
    returned.  The function is intentionally forgiving so the register helper
    never fails because of a missing or malformed file during local iterations.
    """

    if not path.exists():
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    if isinstance(data, list):
        # Ensure all entries are mutable dicts for downstream updates.
        return [dict(item) for item in data if isinstance(item, MutableMapping)]
    return []


def _write_catalog(path: Path, data: Sequence[MutableMapping[str, object]]) -> None:
    """Write ``data`` to ``path`` using a stable, pretty-printed format."""

    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(list(data), indent=2, sort_keys=False)
    path.write_text(text + "\n", encoding="utf-8")


def _normalise_tools(tools: Iterable[str]) -> List[str]:
    """Return ``tools`` as a list with duplicates removed, preserving order."""

    seen = set()
    normalised: List[str] = []
    for item in tools:
        if item not in seen:
            normalised.append(item)
            seen.add(item)
    return normalised


def _generate_unique_id(used: set[str]) -> str:
    """Return a random hexadecimal identifier that is not present in ``used``."""

    while True:
        candidate = uuid4().hex
        if candidate not in used:
            used.add(candidate)
            return candidate


def register_tutorial(
    *,
    step_name: str,
    description: str,
    tutorial_path: str,
    tools: Iterable[str],
    catalog_path: str | Path | None = None,
) -> None:
    """Register or update metadata for a tutorial notebook.

    Parameters
    ----------
    step_name:
        Human readable name of the automation step (e.g. ``"TBCollector"``).
    description:
        Short description of the automation showcased by the notebook.
    tutorial_path:
        File name of the generated notebook relative to the repository root.
    tools:
        Iterable of tool names that comprise the documented toolset.
    catalog_path:
        Optional explicit path to the catalogue JSON.  When omitted the default
        ``notebooks/tutorial_catalog.json`` file is used.
    """

    path = Path(catalog_path) if catalog_path is not None else DEFAULT_CATALOG_PATH
    data = _load_catalog(path)

    # Track used identifiers across the full catalogue so new IDs remain unique.
    used_ids: set[str] = set()
    for entry in data:
        entry_id = entry.get("id")
        if isinstance(entry_id, str):
            used_ids.add(entry_id)
        for toolset in entry.get("toolsets", []):
            if isinstance(toolset, MutableMapping):
                toolset_id = toolset.get("id")
                if isinstance(toolset_id, str):
                    used_ids.add(toolset_id)

    # Locate or create the step entry.
    step_entry: MutableMapping[str, object] | None = None
    for entry in data:
        if entry.get("name") == step_name:
            step_entry = entry
            break

    if step_entry is None:
        step_entry = {
            "id": _generate_unique_id(used_ids),
            "name": step_name,
            "description": description,
            "toolsets": [],
        }
        data.append(step_entry)
    else:
        # Update description to keep catalogue fresh; do not mutate ID.
        step_entry["description"] = description
        if "toolsets" not in step_entry or not isinstance(step_entry["toolsets"], list):
            step_entry["toolsets"] = []

    toolsets = step_entry.setdefault("toolsets", [])
    assert isinstance(toolsets, list)  # for type checkers

    normalised_tools = _normalise_tools(tools)
    tutorial_name = str(tutorial_path)

    toolset_entry: MutableMapping[str, object] | None = None
    for item in toolsets:
        if isinstance(item, MutableMapping) and item.get("tutorial") == tutorial_name:
            toolset_entry = item
            break

    if toolset_entry is None:
        toolset_entry = {
            "id": _generate_unique_id(used_ids),
            "tutorial": tutorial_name,
            "tools": normalised_tools,
        }
        toolsets.append(toolset_entry)
    else:
        toolset_entry["tools"] = normalised_tools

    # Sort entries for reproducible diffs.
    data.sort(key=lambda item: str(item.get("name", "")))
    for entry in data:
        toolset_list = entry.get("toolsets")
        if isinstance(toolset_list, list):
            toolset_list.sort(key=lambda item: str(item.get("tutorial", "")))

    _write_catalog(path, data)


__all__ = ["register_tutorial", "DEFAULT_CATALOG_PATH"]

