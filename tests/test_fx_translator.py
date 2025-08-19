from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from core.io_utils import write_excel, read_excel
from plugins.fx_translator import FXTranslator


def test_applies_fx_rates(tmp_path):
    tb_dir = tmp_path / "tb"
    fx_dir = tmp_path / "fx"
    tb_dir.mkdir(); fx_dir.mkdir()

    master = [
        {"EntityCode": "E1", "AccountCode": "A1", "Debit": 100, "Credit": 0, "CurrencyCode": "USD"},
        {"EntityCode": "E2", "AccountCode": "A1", "Debit": 0, "Credit": 200, "CurrencyCode": "EUR"},
    ]
    rates = [
        {"CurrencyCode": "USD", "FXRate": 1},
        {"CurrencyCode": "EUR", "FXRate": 1.1},
    ]
    write_excel(master, tb_dir / "Master_TB_202301.xlsx")
    write_excel(rates, fx_dir / "Rates_202301.xlsx")

    cfg = {"params": {"fx_source": "file"}, "reporting_currency": "USD"}
    folders = {"tb": tb_dir.as_posix(), "fx": fx_dir.as_posix()}
    naming = {"master_tb": "Master_TB_{period}.xlsx", "fx_rates": "Rates_{period}.xlsx", "fx_adjustments": "FXAdj_{period}.xlsx"}
    step = FXTranslator(cfg, folders, naming, period="202301")

    io = step.plan_io()
    result = step.run(io)

    assert result.success
    adjusted = read_excel(io.outputs["adjusted_tb"])
    assert float(adjusted[1]["FXRate"]) == 1.1
    assert float(adjusted[1]["ReportingCurrencyAmount"]) == round((0 - 200) * 1.1, 2)
    fx_adj = read_excel(io.outputs["fx_adjustments"])
    assert fx_adj[0]["Period"] == "202301"
