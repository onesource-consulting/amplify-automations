"""Notebook-style snippet for running ClientEngagementLetterDraft standalone."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

import sys

sys.path.append(str(Path.cwd() / "src"))

from amplify_automations.core.io_utils import write_excel  # noqa: E402
from amplify_automations.core.contracts import StepIO  # noqa: E402
from amplify_automations.plugins.client_engagement_letter_draft import (  # noqa: E402
    ClientEngagementLetterDraft,
)


period = "202501"
support_dir = Path("./data/Finance/Engagements")
support_dir.mkdir(parents=True, exist_ok=True)

metadata_path = support_dir / f"client_metadata_{period}.json"
metadata_path.write_text(
    json.dumps(
        [
            {
                "ClientID": "C-1001",
                "ClientName": "Acme Holdings",
                "FiscalYear": "2025",
                "ServiceLines": ["CONSULT", "TAX"],
            }
        ],
        indent=2,
    ),
    encoding="utf-8",
)

write_excel(
    [
        {"ServiceLineCode": "CONSULT", "Description": "Consulting Services", "Rate": 250},
        {"ServiceLineCode": "TAX", "Description": "Tax Advisory", "Rate": 180},
    ],
    (support_dir / "service_lines.xlsx").as_posix(),
    headers=["ServiceLineCode", "Description", "Rate"],
)

template_path = support_dir / "Engagement_Letter_Template.dotx"
template_path.write_text(
    "Engagement Letter for {{ClientName}}\nServices:\n{{ServiceSummary}}\nFiscal Year FY{{FiscalYear}}\n",
    encoding="utf-8",
)

cfg = {
    "params": {
        "client_metadata": "{support}/client_metadata_{period}.json",
        "service_lines": "{support}/service_lines.xlsx",
        "template_path": "{support}/Engagement_Letter_Template.dotx",
        "output_folder": "{support}/Drafts_{period}",
        "manifest_path": "{support}/Drafts_{period}/manifest.json",
        "notification_log": "{support}/Drafts_{period}/notifications.txt",
        "notification_recipients": ["teams://StaffAccountant"],
    }
}
folders = {"support": str(support_dir), "root": "./data/Finance"}
naming: Dict[str, str] = {}

step = ClientEngagementLetterDraft(cfg, folders, naming, period)
io_plan: StepIO = step.plan_io()
result = step.run(io_plan)

print(result.ok)
print(result.messages)
print(result.metrics)
