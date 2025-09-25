"""Build a tutorial notebook for the Client Engagement Letter Draft step."""

from __future__ import annotations

from pathlib import Path
import json

try:
    import nbformat as nbf
except Exception:  # pragma: no cover - ensure nbformat is available when script runs
    import subprocess, sys

    subprocess.check_call([sys.executable, "-m", "pip", "install", "nbformat"])
    import nbformat as nbf  # type: ignore


def md(text: str):
    """Return a markdown cell."""

    return nbf.v4.new_markdown_cell(text)


def code(text: str):
    """Return a code cell."""

    return nbf.v4.new_code_cell(text)


ROOT = Path(__file__).parent


def build_notebook() -> None:
    period = "202501"
    support_dir = "./data/Finance/Engagements"

    cells: list = []

    cells.append(
        md(
            "# Client Engagement Letter Draft — Hands-on Tutorial\n"
            "This notebook walks through configuring the **ClientEngagementLetterDraft** step,"
            " creating sample inputs, running the automation, and reviewing the generated outputs."
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
        "for _pkg in ['pandas', 'openpyxl']:\n"
        "    _ensure(_pkg)\n"
        "from pathlib import Path\n"
        "ROOT = Path.cwd()\n"
        "sys.path.append(str(ROOT / 'src'))\n"
        "print('Project source path added:', ROOT / 'src')\n"
    )
    cells.append(code(env_setup))

    cells.append(
        md(
            "## 1. Create sample engagement data\n"
            "We'll stage demo metadata, service line rates, and a template document inside"
            f" `{support_dir}` for reporting period **{period}**."
        )
    )

    data_setup = (
        "from pathlib import Path\n"
        "import json\n"
        "from amplify_automations.core.io_utils import write_excel\n\n"
        f"PERIOD = '{period}'\n"
        f"SUPPORT_DIR = Path('{support_dir}')\n"
        "SUPPORT_DIR.mkdir(parents=True, exist_ok=True)\n\n"
        "metadata = [\n"
        "    {\n"
        "        'ClientID': 'C-1001',\n"
        "        'ClientName': 'Acme Holdings',\n"
        "        'FiscalYear': '2025',\n"
        "        'ServiceLines': ['CONSULT', 'TAX'],\n"
        "    },\n"
        "    {\n"
        "        'ClientID': 'C-2040',\n"
        "        'ClientName': 'Global Manufacturing',\n"
        "        'FiscalYear': '2025',\n"
        "        'ServiceLines': ['AUDIT'],\n"
        "    },\n"
        "]\n"
        "metadata_path = SUPPORT_DIR / f'client_metadata_{PERIOD}.json'\n"
        "metadata_path.write_text(json.dumps(metadata, indent=2), encoding='utf-8')\n\n"
        "service_lines = [\n"
        "    {'ServiceLineCode': 'CONSULT', 'Description': 'Consulting Services', 'Rate': 250},\n"
        "    {'ServiceLineCode': 'TAX', 'Description': 'Tax Advisory', 'Rate': 180},\n"
        "    {'ServiceLineCode': 'AUDIT', 'Description': 'Audit and Assurance', 'Rate': 310},\n"
        "]\n"
        "write_excel(\n"
        "    service_lines,\n"
        "    (SUPPORT_DIR / 'service_lines.xlsx').as_posix(),\n"
        "    headers=['ServiceLineCode', 'Description', 'Rate'],\n"
        ")\n\n"
        "template_path = SUPPORT_DIR / 'Engagement_Letter_Template.dotx'\n"
        "template_path.write_text(\n"
        "    (\n"
        "        'Engagement Letter for {{ClientName}}\\n'\n"
        "        'Services:\\n{{ServiceSummary}}\\n'\n"
        "        'Fiscal Year FY{{FiscalYear}}\\nPrepared {{GeneratedOn}}\\n'\n"
        "    ),\n"
        "    encoding='utf-8',\n"
        ")\n\n"
        "print('Client metadata →', metadata_path)\n"
        "print('Service lines workbook →', SUPPORT_DIR / 'service_lines.xlsx')\n"
        "print('Template path →', template_path)\n"
    )
    cells.append(code(data_setup))

    cells.append(
        md(
            "## 2. Review the staged inputs\n"
            "Inspect the JSON metadata and the Excel service line reference to understand the"
            " structure expected by the automation."
        )
    )

    inspect_inputs = (
        "import json\n"
        "from amplify_automations.core.io_utils import read_excel\n\n"
        "with open(metadata_path, encoding='utf-8') as f:\n"
        "    print(json.dumps(json.load(f), indent=2))\n\n"
        "service_table = read_excel((SUPPORT_DIR / 'service_lines.xlsx').as_posix())\n"
        "service_table"
    )
    cells.append(code(inspect_inputs))

    cells.append(
        md(
            "## 3. Configure and run the step\n"
            "We provide folder mappings, parameter placeholders, and then execute the"
            " `ClientEngagementLetterDraft` step to generate draft letters."
        )
    )

    run_step = (
        "from amplify_automations.plugins.client_engagement_letter_draft import ClientEngagementLetterDraft\n"
        "from amplify_automations.core.contracts import StepIO\n\n"
        "cfg = {\n"
        "    'params': {\n"
        "        'client_metadata': '{support}/client_metadata_{period}.json',\n"
        "        'service_lines': '{support}/service_lines.xlsx',\n"
        "        'template_path': '{support}/Engagement_Letter_Template.dotx',\n"
        "        'output_folder': '{support}/Drafts_{period}',\n"
        "        'manifest_path': '{support}/Drafts_{period}/manifest.json',\n"
        "        'notification_log': '{support}/Drafts_{period}/notifications.txt',\n"
        "        'notification_recipients': ['teams://StaffAccountant'],\n"
        "    }\n"
        "}\n"
        "folders = {'support': str(SUPPORT_DIR), 'root': './data/Finance'}\n"
        "naming = {}\n\n"
        "step = ClientEngagementLetterDraft(cfg, folders, naming, PERIOD)\n"
        "io_plan: StepIO = step.plan_io()\n"
        "result = step.run(io_plan)\n"
        "print('Success:', result.ok)\n"
        "print('Messages:', result.messages)\n"
        "result.metrics"
    )
    cells.append(code(run_step))

    cells.append(
        md(
            "## 4. Inspect generated artifacts\n"
            "The step outputs letters (as `.docx` text files for the tutorial), a JSON manifest,"
            " and a notification log summarising who to alert."
        )
    )

    inspect_outputs = (
        "from pathlib import Path\n"
        "letters_dir = Path(io_plan.outputs['letters_dir'])\n"
        "manifest_path = Path(io_plan.outputs['manifest'])\n"
        "notification_path = Path(io_plan.outputs['notification_log'])\n\n"
        "print('Letters directory:', letters_dir)\n"
        "print('Generated files:', [p.name for p in letters_dir.glob('*.docx')])\n\n"
        "print('Manifest preview:')\n"
        "print(manifest_path.read_text(encoding='utf-8'))\n\n"
        "print('Notification log:')\n"
        "print(notification_path.read_text(encoding='utf-8'))\n"
    )
    cells.append(code(inspect_outputs))

    cells.append(
        md(
            "## 5. Next steps\n"
            "- Replace the sample metadata export with your CRM/ERP client roster.\n"
            "- Expand `service_lines.xlsx` to include billing terms, partners, or delivery details.\n"
            "- Drop a prior year folder into the config (`prior_letters_folder`) to roll forward letters.\n"
            "- Integrate the step into a full finance pipeline or schedule it inside your orchestration tooling."
        )
    )

    nb = nbf.v4.new_notebook()
    nb["cells"] = cells
    nb["metadata"]["language_info"] = {"name": "python"}

    out_path = ROOT / "Client_Engagement_Letter_Draft_Tutorial.ipynb"
    with out_path.open("w", encoding="utf-8") as fh:
        nbf.write(nb, fh)

    print(f"Wrote {out_path.name} — open it in Jupyter and Run All to experience the tutorial.")


if __name__ == "__main__":
    build_notebook()
