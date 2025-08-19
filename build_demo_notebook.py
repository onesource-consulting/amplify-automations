import json
from pathlib import Path

try:
    import nbformat as nbf
except Exception:  # pragma: no cover - ensure availability
    import subprocess, sys
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'nbformat'])
    import nbformat as nbf


def md(text: str):
    return nbf.v4.new_markdown_cell(text)


def code(text: str):
    return nbf.v4.new_code_cell(text)


root = Path(__file__).parent


def read_file(path: Path) -> str | None:
    try:
        return path.read_text()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Default pipeline configuration (JSON-formatted YAML)
# ---------------------------------------------------------------------------
default_cfg = {
    "period": "202501",
    "reporting_currency": "USD",
    "folders": {
        "root": "./data/Finance",
        "mapping": "./data/Finance/Mapping",
        "tb": "./data/Finance/Consolidation/TB",
        "ic": "./data/Finance/IC",
        "fx": "./data/Finance/FX",
        "eliminations": "./data/Finance/Eliminations",
        "support": "./data/Finance/Support",
        "approvals": "./data/Finance/Approvals",
    },
    "naming": {
        "tb_pattern": "TB_{entity}_{period}.xlsx",
        "master_tb": "Master_TB_{period}.xlsx",
        "fx_rates": "FX_Rates_{period}.xlsx",
        "fx_adjustments": "FX_Adjustments_{period}.xlsx",
        "support_pdf": "Support_{period}.pdf",
    },
    "pipeline": [
        {
            "step": "TBCollector",
            "params": {
                "required_columns": [
                    "EntityCode",
                    "AccountCode",
                    "AccountName",
                    "Debit",
                    "Credit",
                    "Period",
                    "CurrencyCode",
                ],
                "enforce_balanced": True,
            },
        },
        {
            "step": "FXTranslator",
            "params": {
                "fx_source": "file",
                "file": "{fx}/FX_Rates_{period}.xlsx",
                "required_columns": [
                    "CurrencyCode",
                    "FXRate",
                    "Period",
                    "Source",
                ],
                "tolerance": 5,
            },
        },
        {
            "step": "PDFAssembler",
            "params": {
                "include": [
                    "{tb}/Master_TB_{period}.xlsx",
                    "{fx}/FX_Adjustments_{period}.xlsx",
                ]
            },
        },
    ],
}


def get_pipeline_text() -> str:
    p = root / "config/pipeline.yaml"
    text = read_file(p)
    if text and "Reference[" not in text:
        return text
    return json.dumps(default_cfg, indent=2)


PIPELINE_TEXT = get_pipeline_text()


# ---------------------------------------------------------------------------
# Module definitions to embed
# ---------------------------------------------------------------------------
modules = [
    (
        "src/core/contracts.py",
        "core.contracts",
        ["StepIO", "ValidationResult", "StepLog"],
        """
from dataclasses import dataclass, field
from typing import Dict, List, Any


@dataclass
class StepIO:
    inputs: Dict[str, str]
    outputs: Dict[str, str]


@dataclass
class ValidationResult:
    ok: bool
    messages: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.ok


@dataclass
class StepLog:
    step_name: str
    period: str
    status: str
    messages: List[str]
    metrics: Dict[str, Any]
    input_hashes: Dict[str, str]
    output_hashes: Dict[str, str]
""",
    ),
    (
        "src/core/step_base.py",
        "core.step_base",
        ["Step"],
        """
from abc import ABC, abstractmethod
from typing import Any, Dict
from core.contracts import StepIO, ValidationResult


class Step(ABC):
    name: str = "BaseStep"

    def __init__(self, cfg: Dict[str, Any], folders: Dict[str, str], naming: Dict[str, str], period: str) -> None:
        self.cfg = cfg
        self.folders = folders
        self.naming = naming
        self.period = period

    @abstractmethod
    def plan_io(self) -> StepIO: ...

    @abstractmethod
    def run(self, io: StepIO) -> ValidationResult: ...

    def before(self, io: StepIO) -> None: ...

    def after(self, io: StepIO, vr: ValidationResult) -> None: ...
""",
    ),
    (
        "src/core/registry.py",
        "core.registry",
        ["register", "get_step", "get"],
        """
from typing import Callable, Dict, Type

_REGISTRY: Dict[str, Type] = {}


def register(name: str):
    def _wrap(cls):
        _REGISTRY[name] = cls
        return cls

    return _wrap


def get_step(name: str):
    return _REGISTRY[name]


get = get_step
""",
    ),
    (
        "src/core/io_utils.py",
        "core.io_utils",
        ["expand", "file_hash", "write_excel", "read_excel", "HAS_PANDAS"],
        None,
    ),
    (
        "src/core/validation_utils.py",
        "core.validation_utils",
        ["require_columns", "debits_equal_credits"],
        None,
    ),
    (
        "src/core/normalization.py",
        "core.normalization",
        [
            "SCHEMAS",
            "COLUMN_ALIASES",
            "resolve_columns",
            "coerce_tb_types",
            "infer_period_from_filename",
            "infer_entity_from_filename",
            "load_fx_rates",
        ],
        """
SCHEMAS = {
    'TB': ['EntityCode','AccountCode','AccountName','Debit','Credit','Period','CurrencyCode'],
    'FX_RATES': ['CurrencyCode','FXRate','Period','Source'],
}
COLUMN_ALIASES = {
    'EntityCode': ['Entity','Company'],
    'AccountCode': ['Account','GL'],
    'AccountName': ['AccountName'],
    'Debit': ['Debit'],
    'Credit': ['Credit'],
    'Period': ['Period'],
    'CurrencyCode': ['CurrencyCode'],
}


def resolve_columns(df, target, aliases):
    return df


def coerce_tb_types(df):
    return df


def infer_period_from_filename(path):
    return None


def infer_entity_from_filename(path):
    return None


def load_fx_rates(path_or_api):
    return {}
""",
    ),
]


plugins = [
    (
        "src/plugins/tb_collector.py",
        "plugins.tb_collector",
        ["TBCollector"],
        None,
    ),
    (
        "src/plugins/fx_translator.py",
        "plugins.fx_translator",
        ["FXTranslator"],
        None,
    ),
    (
        "src/plugins/pdf_assembler.py",
        "plugins.pdf_assembler",
        ["PDFAssembler"],
        None,
    ),
]


# Runner file with fallback implementation appended
runner_path = root / "src/runner.py"
runner_text = read_file(runner_path) or ""
if not runner_text.endswith("\n"):
    runner_text += "\n"
runner_extra = (
    "import json\n"
    "from core.registry import get_step\n"
    "from core.step_base import Step\n"
    "\n"
    "# Minimal runner implementation\n"
    "def run_pipeline(cfg_path: str):\n"
    "    with open(cfg_path) as f:\n"
    "        cfg = json.load(f)\n"
    "    period = cfg.get('period')\n"
    "    folders = cfg.get('folders', {})\n"
    "    naming = cfg.get('naming', {})\n"
    "    results = []\n"
    "    for step_cfg in cfg.get('pipeline', []):\n"
    "        step_name = step_cfg['step']\n"
    "        step_conf = {**cfg, **step_cfg}\n"
    "        cls = get_step(step_name)\n"
    "        step = cls(step_conf, folders, naming, period)\n"
    "        io = step.plan_io()\n"
    "        step.before(io)\n"
    "        vr = step.run(io)\n"
    "        step.after(io, vr)\n"
    "        results.append((step_name, vr.ok, vr.messages))\n"
    "        if not vr.ok:\n"
    "            break\n"
    "    return results\n"
)
runner_full = runner_text + runner_extra


# ---------------------------------------------------------------------------
# Build notebook cells
# ---------------------------------------------------------------------------
cells: list = []

cells.append(
    md(
        "# Financial Consolidation — Modular Demo (End-to-End)\n"
        "This notebook is a self-contained demo. It copy-pastes core project files into cells so the sources remain untouched while illustrating a modular consolidation pipeline."
    )
)

env_setup = (
    "import sys, subprocess\n"
    "print(sys.version)\n\n"
    "def _ensure(pkg):\n"
    "    try:\n"
    "        __import__(pkg)\n"
    "    except Exception:\n"
    "        subprocess.check_call([sys.executable, '-m', 'pip', 'install', pkg])\n"
    "for _p in ['pandas', 'openpyxl', 'requests', 'PyPDF2', 'fpdf']:\n"
    "    _ensure(_p)\n"
    "from pathlib import Path\n"
    "ROOT = Path.cwd()\n"
)
cells.append(code(env_setup))

cells.append(
    md(
        "### Folder & Config Conventions\n"
        "The pipeline expects a Finance directory with subfolders such as Mapping, Consolidation/TB, FX, Support and others. Files follow patterns like `TB_{Entity}_{YYYYMM}.xlsx` where `{YYYYMM}` represents the reporting period."
    )
)

pipe_code = (
    "PIPELINE_YAML = '''\n" + PIPELINE_TEXT + "\n'''\n"
    "from pathlib import Path as _Path\n"
    "_Path('config').mkdir(parents=True, exist_ok=True)\n"
    "_Path('config/pipeline.yaml').write_text(PIPELINE_YAML)\n"
)
cells.append(code(pipe_code))

cells.append(md("### Core Contracts"))

# Embed core modules
for path, module_name, exports, fallback in modules:
    p = root / path
    text = read_file(p)
    if text is None:
        text = fallback or ""
    if not text.endswith("\n"):
        text += "\n"
    exports_list = ", ".join([f"'{e}'" for e in exports])
    cell_text = (
        f"# [embed] {path}\n" + text +
        "# register module\n"
        "import sys, types as _types\n"
        f"_mod = _types.ModuleType('{module_name}')\n"
        f"for _n in [{exports_list}]:\n"
        "    _mod.__dict__[_n] = globals().get(_n)\n"
        f"sys.modules['{module_name}'] = _mod\n"
        f"_pkg = sys.modules.setdefault('{module_name.split('.')[0]}', _types.ModuleType('{module_name.split('.')[0]}'))\n"
        f"setattr(_pkg, '{module_name.split('.')[1]}', _mod)\n"
    )
    cells.append(code(cell_text))
    if path.endswith("contracts.py"):
        cells.append(md("### Step Base"))
    elif path.endswith("step_base.py"):
        cells.append(md("### Registry"))
    elif path.endswith("registry.py"):
        cells.append(md("### I/O Utilities"))
    elif path.endswith("io_utils.py"):
        cells.append(md("### Validation Utilities"))
    elif path.endswith("validation_utils.py"):
        cells.append(md("### Normalization — optional"))

# Plugins overview
cells.append(md("### Plugins Overview"))
for path, module_name, exports, fallback in plugins:
    p = root / path
    text = read_file(p)
    if text is None:
        text = fallback or ""
    if not text.endswith("\n"):
        text += "\n"
    exports_list = ", ".join([f"'{e}'" for e in exports])
    cell_text = (
        f"# [embed] {path}\n" + text +
        "# register module\n"
        "import sys, types as _types\n"
        f"_mod = _types.ModuleType('{module_name}')\n"
        f"for _n in [{exports_list}]:\n"
        "    _mod.__dict__[_n] = globals().get(_n)\n"
        f"sys.modules['{module_name}'] = _mod\n"
        f"_pkg = sys.modules.setdefault('{module_name.split('.')[0]}', _types.ModuleType('{module_name.split('.')[0]}'))\n"
        f"setattr(_pkg, '{module_name.split('.')[1]}', _mod)\n"
    )
    cells.append(code(cell_text))

cells.append(md("### Runner"))
runner_cell = (
    "# [embed] src/runner.py\n" + runner_full +
    "# register runner module\n"
    "import sys, types as _types\n"
    "_mod = _types.ModuleType('runner')\n"
    "_mod.run_pipeline = run_pipeline\n"
    "sys.modules['runner'] = _mod\n"
)
cells.append(code(runner_cell))

cells.append(
    md(
        "### Create sample practice data\n"
        "We'll generate minimal trial balance and FX rate files under `./data/Finance/...` for a fictitious period 202501."
    )
)

gen_data = (
    "from core.io_utils import write_excel\n"
    "from pathlib import Path\n\n"
    "root = Path('./data/Finance')\n"
    "(root / 'Consolidation/TB').mkdir(parents=True, exist_ok=True)\n"
    "(root / 'FX').mkdir(parents=True, exist_ok=True)\n\n"
    "headers_tb = ['EntityCode','AccountCode','AccountName','Debit','Credit','Period','CurrencyCode']\n"
    "rows_us = [\n"
    "    {'EntityCode':'US','AccountCode':'1000','AccountName':'Cash','Debit':100.0,'Credit':0.0,'Period':'202501','CurrencyCode':'USD'},\n"
    "    {'EntityCode':'US','AccountCode':'2000','AccountName':'Revenue','Debit':0.0,'Credit':100.0,'Period':'202501','CurrencyCode':'USD'},\n"
    "]\n"
    "rows_gb = [\n"
    "    {'EntityCode':'GB','AccountCode':'1000','AccountName':'Cash','Debit':80.0,'Credit':0.0,'Period':'202501','CurrencyCode':'GBP'},\n"
    "    {'EntityCode':'GB','AccountCode':'2000','AccountName':'Revenue','Debit':0.0,'Credit':80.0,'Period':'202501','CurrencyCode':'GBP'},\n"
    "]\n"
    "write_excel(rows_us, './data/Finance/Consolidation/TB/TB_US_202501.xlsx', headers_tb)\n"
    "write_excel(rows_gb, './data/Finance/Consolidation/TB/TB_GB_202501.xlsx', headers_tb)\n\n"
    "headers_fx = ['CurrencyCode','FXRate','Period','Source']\n"
    "rates = [\n"
    "    {'CurrencyCode':'USD','FXRate':1.0,'Period':'202501','Source':'Demo'},\n"
    "    {'CurrencyCode':'GBP','FXRate':1.28,'Period':'202501','Source':'Demo'},\n"
    "]\n"
    "write_excel(rates, './data/Finance/FX/FX_Rates_202501.xlsx', headers_fx)\n"
)
cells.append(code(gen_data))

cells.append(md("### Run the pipeline\nImport the plugin modules so they register with the registry, then execute `run_pipeline`."))

run_cell = (
    "import importlib\n"
    "for mod in ['plugins.tb_collector','plugins.fx_translator','plugins.pdf_assembler']:\n"
    "    importlib.import_module(mod)\n"
    "from runner import run_pipeline\n"
    "print(run_pipeline('config/pipeline.yaml'))\n"
)
cells.append(code(run_cell))

cells.append(md("### Inspect Outputs"))

inspect_cell = (
    "from core.io_utils import read_excel, HAS_PANDAS\n"
    "from pathlib import Path\n\n"
    "period = '202501'\n"
    "master_path = Path(f'./data/Finance/Consolidation/TB/Master_TB_{period}.xlsx')\n"
    "fx_path = Path(f'./data/Finance/FX/FX_Adjustments_{period}.xlsx')\n"
    "print('Master TB:', master_path)\n"
    "master = read_excel(master_path.as_posix())\n"
    "fx = read_excel(fx_path.as_posix())\n"
    "if HAS_PANDAS:\n"
    "    import pandas as pd  # type: ignore\n"
    "    display(pd.DataFrame(master).head())\n"
    "    display(pd.DataFrame(master).tail())\n"
    "    display(pd.DataFrame(fx).head())\n"
    "    display(pd.DataFrame(fx).tail())\n"
    "else:\n"
    "    print(master[:5])\n"
    "    print(master[-5:])\n"
    "    print(fx[:5])\n"
    "    print(fx[-5:])\n\n"
    "support_path = Path(f'./data/Finance/Support/Support_{period}.pdf')\n"
    "print('Support PDF:', support_path)\n"
    "try:\n"
    "    from PyPDF2 import PdfReader\n"
    "    reader = PdfReader(str(support_path))\n"
    "    print('Pages:', len(reader.pages))\n"
    "except Exception:\n"
    "    lines = support_path.read_text().splitlines()\n"
    "    print('Lines in PDF text:', len(lines))\n\n"
    "log_path = Path('./data/Finance/Support/Automation_Log.xlsx')\n"
    "if log_path.exists():\n"
    "    log = read_excel(log_path.as_posix())\n"
    "    print(log if not HAS_PANDAS else pd.DataFrame(log))\n"
    "else:\n"
    "    print('No automation log generated.')\n"
)
cells.append(code(inspect_cell))

cells.append(md("### Next steps\nSwap the practice data for real finance system exports and extend the pipeline by adding new plugin modules following the patterns above."))


# Assemble notebook
nb = nbf.v4.new_notebook()
nb["cells"] = cells
nb["metadata"]["language_info"] = {"name": "python"}

out_path = root / "Financial_Consolidation_Demo.ipynb"
with out_path.open("w", encoding="utf-8") as f:
    nbf.write(nb, f)

print(f"Wrote {out_path.name} — open it and Run All to see the full consolidation demo.")

