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
from pathlib import Path, PurePosixPath
from typing import Iterable, List, Sequence, Tuple
from uuid import UUID, uuid4


DEFAULT_CATALOG_DIRECTORY = Path("notebooks")
# ``DEFAULT_CATALOG_PATH`` is retained for backwards compatibility with previous
# releases that imported it directly.  It now points at the notebooks directory
# rather than a specific file because catalogue filenames are derived from the
# step identifier at runtime.
DEFAULT_CATALOG_PATH = DEFAULT_CATALOG_DIRECTORY


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


_TRAILING_DESCRIPTOR_KEYWORDS: Tuple[str, ...] = (
    "mock",
    "sandbox",
    "integration",
    "automation",
    "workflow",
    "templating",
)


def _simplify_tool_name(tool: str) -> str:
    """Return ``tool`` without trailing descriptive phrases.

    Tutorials sometimes describe tools with phrases such as
    ``"Deltek Vantagepoint mock API integration"``.  The catalogue should
    capture only the underlying software names so that downstream consumers can
    group tutorials by the same tool regardless of how the author phrased the
    description.  This helper trims the trailing descriptor when it starts with
    one of the keywords in :data:`_TRAILING_DESCRIPTOR_KEYWORDS`.
    """

    if not isinstance(tool, str):
        return ""

    name = " ".join(tool.split()).strip()
    if not name:
        return ""

    lower_name = name.casefold()
    for keyword in _TRAILING_DESCRIPTOR_KEYWORDS:
        marker = f" {keyword}"
        idx = lower_name.find(marker)
        if idx != -1:
            name = name[:idx]
            lower_name = lower_name[:idx]

    simplified = name.strip()
    return simplified or ""


def _normalise_tools(tools: Iterable[str]) -> List[str]:
    """Return simplified tool names with duplicates removed, preserving order."""

    seen = set()
    normalised: List[str] = []
    for item in tools:
        simplified = _simplify_tool_name(item)
        if simplified and simplified not in seen:
            normalised.append(simplified)
            seen.add(simplified)
    return normalised


def _normalise_tutorial_reference(value: str | Path) -> str:
    """Return a canonical tutorial notebook reference without the ``notebooks`` prefix."""

    path = Path(value)
    parts = list(path.parts)
    if parts and parts[0] == "notebooks":
        parts = parts[1:]

    if not parts:
        return ""

    return str(PurePosixPath(*parts))


def _canonicalise_uuid(value: str) -> str | None:
    """Return ``value`` as a canonical UUID string if possible."""

    try:
        return str(UUID(value))
    except (TypeError, ValueError, AttributeError):
        return None


def _generate_unique_id(used: set[str]) -> str:
    """Return a random UUID identifier that is not present in ``used``."""

    while True:
        candidate = str(uuid4())
        if candidate not in used:
            used.add(candidate)
            return candidate


def _discover_catalog_for_step(step_name: str) -> Tuple[Path | None, List[MutableMapping[str, object]]]:
    """Return the catalogue path and data for ``step_name`` if it already exists."""

    directory = DEFAULT_CATALOG_DIRECTORY
    if not directory.exists():
        return None, []

    for candidate in sorted(directory.glob("*.json")):
        data = _load_catalog(candidate)
        for entry in data:
            if entry.get("name") == step_name:
                return candidate, data

    return None, []


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
        Optional explicit path to the catalogue JSON.  When omitted the helper
        stores entries in ``notebooks/<step-id>.json`` where ``<step-id>`` is the
        UUID assigned to the automation step.  If a catalogue for the step
        already exists it is reused regardless of its current filename.
    """

    using_default_location = catalog_path is None
    if catalog_path is not None:
        path = Path(catalog_path)
        data = _load_catalog(path)
    else:
        path, data = _discover_catalog_for_step(step_name)
        if path is None:
            data = []

    # Track used identifiers across the full catalogue so new IDs remain unique.
    used_ids: set[str] = set()
    for entry in data:
        entry_id = entry.get("id")
        if isinstance(entry_id, str):
            canonical = _canonicalise_uuid(entry_id)
            if canonical is not None:
                used_ids.add(canonical)
                if canonical != entry_id:
                    entry["id"] = canonical
            else:
                used_ids.add(entry_id)
        toolset_list = entry.get("toolsets", [])
        if isinstance(toolset_list, list):
            for toolset in toolset_list:
                if isinstance(toolset, MutableMapping):
                    toolset_id = toolset.get("id")
                    if isinstance(toolset_id, str):
                        canonical = _canonicalise_uuid(toolset_id)
                        if canonical is not None:
                            used_ids.add(canonical)
                            if canonical != toolset_id:
                                toolset["id"] = canonical
                        else:
                            used_ids.add(toolset_id)

                    tutorial_ref = toolset.get("tutorial")
                    if isinstance(tutorial_ref, str):
                        normalised_ref = _normalise_tutorial_reference(tutorial_ref)
                        if tutorial_ref != normalised_ref:
                            toolset["tutorial"] = normalised_ref

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
    tutorial_name = _normalise_tutorial_reference(tutorial_path)

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

    if using_default_location:
        step_identifier = str(step_entry["id"])
        final_path = DEFAULT_CATALOG_DIRECTORY / f"{step_identifier}.json"
    else:
        assert path is not None  # for mypy/mind
        final_path = path

    if path is not None and final_path != path and using_default_location:
        _write_catalog(final_path, data)
        if path.exists():
            path.unlink()
    else:
        _write_catalog(final_path, data)


__all__ = ["register_tutorial", "DEFAULT_CATALOG_DIRECTORY", "DEFAULT_CATALOG_PATH"]

