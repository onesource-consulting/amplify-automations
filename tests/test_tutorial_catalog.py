from __future__ import annotations

import json
import re
from pathlib import Path

from amplify_automations.core.tutorial_catalog import register_tutorial


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


UUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

def test_register_tutorial_creates_catalog(tmp_path):
    catalog = tmp_path / "catalog.json"

    register_tutorial(
        step_name="ExampleStep",
        description="Example description",
        tutorial_path="notebooks/example.ipynb",
        tools=["Tool A", "Tool B"],
        catalog_path=catalog,
    )

    data = _load(catalog)
    assert len(data) == 1

    entry = data[0]
    assert entry["name"] == "ExampleStep"
    assert entry["description"] == "Example description"
    assert UUID_PATTERN.match(entry["id"]) is not None

    toolsets = entry["toolsets"]
    assert len(toolsets) == 1
    toolset = toolsets[0]
    assert toolset["tutorial"] == "notebooks/example.ipynb"
    assert toolset["tools"] == ["Tool A", "Tool B"]
    assert UUID_PATTERN.match(toolset["id"]) is not None
    assert toolset["id"] != entry["id"]


def test_register_tutorial_updates_existing_entries(tmp_path):
    catalog = tmp_path / "catalog.json"

    register_tutorial(
        step_name="ExampleStep",
        description="Old description",
        tutorial_path="notebooks/example.ipynb",
        tools=["Tool A", "Tool B"],
        catalog_path=catalog,
    )

    original = _load(catalog)[0]
    original_step_id = original["id"]
    original_toolset_id = original["toolsets"][0]["id"]

    register_tutorial(
        step_name="ExampleStep",
        description="Refreshed description",
        tutorial_path="notebooks/example.ipynb",
        tools=["Tool B", "Tool A", "Tool A"],
        catalog_path=catalog,
    )

    updated = _load(catalog)[0]
    assert UUID_PATTERN.match(updated["id"]) is not None
    assert updated["id"] == original_step_id
    assert updated["description"] == "Refreshed description"

    toolset = updated["toolsets"][0]
    assert UUID_PATTERN.match(toolset["id"]) is not None
    assert toolset["id"] == original_toolset_id
    # Tools are de-duplicated but order respects first appearance
    assert toolset["tools"] == ["Tool B", "Tool A"]


def test_register_tutorial_adds_additional_toolsets(tmp_path):
    catalog = tmp_path / "catalog.json"

    register_tutorial(
        step_name="ExampleStep",
        description="Initial",
        tutorial_path="notebooks/example.ipynb",
        tools=["Tool A"],
        catalog_path=catalog,
    )

    register_tutorial(
        step_name="ExampleStep",
        description="Initial",
        tutorial_path="notebooks/example_alt.ipynb",
        tools=["Tool B"],
        catalog_path=catalog,
    )

    data = _load(catalog)
    assert len(data) == 1

    toolsets = data[0]["toolsets"]
    assert len(toolsets) == 2

    tutorials = [toolset["tutorial"] for toolset in toolsets]
    assert tutorials == sorted(tutorials)

    ids = {data[0]["id"]}
    ids.update(toolset["id"] for toolset in toolsets)
    assert len(ids) == 3  # all identifiers should be unique
