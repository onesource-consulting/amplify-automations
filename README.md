# Amplify Automations

Amplify Automations provides a lightweight, plugin‑based framework for automating
financial data workflows.  It includes utilities for normalising trial balances,
applying foreign‑exchange rates and assembling support reports so finance teams
can automate recurring consolidation tasks.

## Features

- **Plugin architecture** – Steps implement a simple `Step` interface and
  register themselves with a global registry.  Built‑in steps include:
  - `TBCollector` — normalises individual trial balance files and merges them
    into a master ledger.
  - `FXTranslator` — applies FX rates to the master trial balance and writes an
    adjustment file.
  - `PDFAssembler` — converts tabular outputs into plain‑text PDF support
    documents.
- **Core utilities** – Helper modules handle I/O, column normalisation,
  validation and logging.

## Installation

```bash
pip install -e .  # from the repository root
```

Python 3.10+ is required.  The package depends on common data libraries such as
`pandas`, `numpy`, `rapidfuzz`, `openpyxl`, `PyPDF2`, `fpdf` and `requests`.

## Quick start

Each step can be executed independently.  The example below collects and merges
trial balance files for a single period:

```python
from amplify_automations.plugins.tb_collector import TBCollector

cfg = {"params": {"required_columns": ["EntityCode", "AccountCode", "Debit", "Credit"]}}
folders = {"tb": "/path/to/tb"}
naming = {"master_tb": "Master_TB_{period}.xlsx"}

step = TBCollector(cfg, folders, naming, period="202301")
io = step.plan_io()
result = step.run(io)
print(result.success, io.outputs["master_tb"])
```

See `build_demo_notebook.py` for an end‑to‑end example that chains multiple
steps together.

## Running the pipeline

To assemble a pipeline, import the desired plugins so they register with the
registry and call `run_pipeline` from `runner.py` using a configuration dict or
YAML file.  Each pipeline item specifies the step name and its parameters.

## Development

### Tests

```bash
pytest
```

### Contributing

1. Fork and clone the repository.
2. Create a branch for your feature or fix.
3. Run the test suite and ensure all checks pass.
4. Submit a pull request.

Contributions for new automation steps or improvements to existing plugins are
welcome.

## License

Distributed under the MIT license; see `LICENSE` for details.

