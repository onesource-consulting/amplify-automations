#!/usr/bin/env python3
"""Example pipeline run for the ClientEngagementLetterDraft step."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(REPO_ROOT / "src"))

from amplify_automations.core.io_utils import write_excel  # noqa: E402
from amplify_automations.runner import run_pipeline  # noqa: E402
from amplify_automations.plugins.client_engagement_letter_draft import (  # noqa: F401,E402
    ClientEngagementLetterDraft,
)


def main() -> None:
    data_root = REPO_ROOT / "data" / "Finance"
    support_dir = data_root / "Engagements"
    support_dir.mkdir(parents=True, exist_ok=True)

    period = "202501"

    # Sample client metadata (JSON)
    client_metadata = [
        {
            "ClientID": "C-1001",
            "ClientName": "Acme Holdings",
            "FiscalYear": "2025",
            "ServiceLines": ["CONSULT", "TAX"],
            "Manager": "manager@example.com",
            "Staff": "staff@example.com",
        },
        {
            "ClientID": "C-2002",
            "ClientName": "Globex International",
            "FiscalYear": "2025",
            "ServiceLineCodes": "AUDIT;ADVISORY",
        },
    ]
    metadata_path = support_dir / f"client_metadata_{period}.json"
    metadata_path.write_text(json.dumps(client_metadata, indent=2), encoding="utf-8")

    # Sample service line reference data (Excel via helper)
    service_lines = [
        {"ServiceLineCode": "CONSULT", "Description": "Consulting Services", "Rate": 250.0},
        {"ServiceLineCode": "TAX", "Description": "Tax Advisory", "Rate": 180.0},
        {"ServiceLineCode": "AUDIT", "Description": "Audit & Assurance", "Rate": 225.0},
        {"ServiceLineCode": "ADVISORY", "Description": "Strategic Advisory", "Rate": 210.0},
    ]
    service_path = support_dir / "service_lines.xlsx"
    write_excel(service_lines, service_path.as_posix(), headers=["ServiceLineCode", "Description", "Rate"])

    # Template with merge fields
    template_text = (
        "Engagement Letter for {{ClientName}}\n"
        "Client ID: {{ClientID}}\n"
        "Fiscal Year: FY{{FiscalYear}}\n\n"
        "Services:\n{{ServiceSummary}}\n\n"
        "Prepared: {{GeneratedOn}}\n"
    )
    template_path = support_dir / "Engagement_Letter_Template.dotx"
    template_path.write_text(template_text, encoding="utf-8")

    # Optional prior year letter to demonstrate roll-forward behaviour
    prior_dir = support_dir / "Prior"
    prior_dir.mkdir(parents=True, exist_ok=True)
    (prior_dir / "Acme_Holdings_EngagementLetter_FY2024.docx").write_text(
        "Prior Year Engagement Letter for {{ClientName}} FY{{FiscalYear}}\nServices:\n{{ServiceSummary}}\n",
        encoding="utf-8",
    )

    pipeline_config = {
        "period": period,
        "folders": {
            "root": str(data_root),
            "support": str(support_dir),
        },
        "naming": {},
        "pipeline": [
            {
                "step": "ClientEngagementLetterDraft",
                "params": {
                    "client_metadata": "{support}/client_metadata_{period}.json",
                    "service_lines": "{support}/service_lines.xlsx",
                    "template_path": "{support}/Engagement_Letter_Template.dotx",
                    "output_folder": "{support}/Drafts_{period}",
                    "manifest_path": "{support}/Drafts_{period}/manifest.json",
                    "notification_log": "{support}/Drafts_{period}/notifications.txt",
                    "prior_letters_folder": "{support}/Prior",
                    "notification_recipients": [
                        "teams://StaffAccountant",
                        "teams://Manager",
                    ],
                },
            }
        ],
    }

    config_dir = REPO_ROOT / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    tmp_config_path = config_dir / "pipeline_client_engagement_letter.yaml"
    tmp_config_path.write_text(yaml.safe_dump(pipeline_config, sort_keys=False), encoding="utf-8")

    logs = run_pipeline(tmp_config_path)
    for log in logs:
        print(f"{log.step_name}: {log.status}")
        for message in log.messages:
            print(f"  - {message}")
        print(f"  metrics: {log.metrics}\n")

    manifest_path = Path(
        pipeline_config["pipeline"][0]["params"]["manifest_path"].format(
            support=str(support_dir),
            period=period,
        )
    )
    print(f"Manifest saved to: {manifest_path}")
    print(manifest_path.read_text(encoding="utf-8"))

    notification_path = Path(
        pipeline_config["pipeline"][0]["params"]["notification_log"].format(
            support=str(support_dir),
            period=period,
        )
    )
    print(f"Notifications log: {notification_path}")
    print(notification_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
