from amplify_automations.core.io_utils import write_excel
from amplify_automations.runner import run_pipeline

# ensure steps register with the registry
from amplify_automations.plugins import tb_collector, fx_translator  # noqa: F401


def test_run_pipeline_executes_steps(tmp_path):
    tb_dir = tmp_path / "tb"
    fx_dir = tmp_path / "fx"
    tb_dir.mkdir()
    fx_dir.mkdir()

    tb1 = [
        {"EntityCode": "E1", "AccountCode": "A1", "Debit": 100, "Credit": 0, "CurrencyCode": "USD"},
        {"EntityCode": "E1", "AccountCode": "A2", "Debit": 0, "Credit": 100, "CurrencyCode": "USD"},
    ]
    tb2 = [
        {"EntityCode": "E2", "AccountCode": "A1", "Debit": 50, "Credit": 0, "CurrencyCode": "EUR"},
        {"EntityCode": "E2", "AccountCode": "A2", "Debit": 0, "Credit": 50, "CurrencyCode": "EUR"},
    ]
    rates = [
        {"CurrencyCode": "USD", "FXRate": 1.0},
        {"CurrencyCode": "EUR", "FXRate": 1.1},
    ]

    write_excel(tb1, tb_dir / "TB_E1_202301.xlsx")
    write_excel(tb2, tb_dir / "TB_E2_202301.xlsx")
    write_excel(rates, fx_dir / "Rates_202301.xlsx")

    cfg = {
        "period": "202301",
        "folders": {"tb": tb_dir.as_posix(), "fx": fx_dir.as_posix()},
        "naming": {
            "master_tb": "Master_TB_{period}.xlsx",
            "fx_rates": "Rates_{period}.xlsx",
            "fx_adjustments": "FXAdj_{period}.xlsx",
        },
        "pipeline": [
            {
                "step": "TBCollector",
                "params": {
                    "required_columns": [
                        "EntityCode",
                        "AccountCode",
                        "Debit",
                        "Credit",
                        "CurrencyCode",
                    ],
                },
            },
            {
                "step": "FXTranslator",
                "params": {
                    "fx_source": "file",
                    "file": "{fx}/Rates_{period}.xlsx",
                    "required_columns": ["CurrencyCode", "FXRate"],
                },
            },
        ],
    }

    logs = run_pipeline(cfg)

    assert len(logs) == 2
    assert all(log.status == "ok" for log in logs)

    master_path = tb_dir / "Master_TB_202301.xlsx"
    adjusted_path = tb_dir / "Master_TB_202301_Adjusted.xlsx"
    fx_adj_path = fx_dir / "FXAdj_202301.xlsx"
    assert master_path.exists()
    assert adjusted_path.exists()
    assert fx_adj_path.exists()

