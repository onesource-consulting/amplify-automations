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
# Build notebook cells
# ---------------------------------------------------------------------------
cells: list = []

cells.append(
    md(
        "# Financial Consolidation — Modular Demo (End-to-End)\n"
        "This notebook references project modules directly so the latest code is used without embedding sources."
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
    "sys.path.append(str(ROOT / 'src'))\n"
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

cells.append(md("### Load project modules"))
load_modules = (
    "from core.io_utils import write_excel, read_excel, HAS_PANDAS\n"
    "import importlib\n"
    "for mod in ['plugins.tb_collector','plugins.fx_translator','plugins.pdf_assembler']:\n"
    "    importlib.import_module(mod)\n"
    "from runner import run_pipeline\n"
)
cells.append(code(load_modules))

cells.append(
    md(
        "### Create sample practice data\n"
        "We'll generate minimal trial balance and FX rate files under `./data/Finance/...` for a fictitious period 202501."
    )
)

gen_data = (
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

cells.append(md("### Run the pipeline"))
run_cell = (
    "print(run_pipeline('config/pipeline.yaml'))\n"
)
cells.append(code(run_cell))

cells.append(md("### Inspect Outputs"))
inspect_cell = (
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

