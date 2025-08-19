from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from core.io_utils import write_excel, read_excel
from plugins.tb_collector import TBCollector


def test_collects_and_merges_trial_balances(tmp_path):
    tb_dir = tmp_path / "tb"
    tb_dir.mkdir()

    tb1 = [
        {"EntityCode": "E1", "AccountCode": "A1", "Debit": 100, "Credit": 0},
        {"EntityCode": "E1", "AccountCode": "A2", "Debit": 0, "Credit": 100},
    ]
    tb2 = [
        {"EntityCode": "E2", "AccountCode": "A1", "Debit": 50, "Credit": 0},
        {"EntityCode": "E2", "AccountCode": "A2", "Debit": 0, "Credit": 50},
    ]
    write_excel(tb1, tb_dir / "TB_E1_202301.xlsx")
    write_excel(tb2, tb_dir / "TB_E2_202301.xlsx")

    cfg = {"params": {"required_columns": ["EntityCode", "AccountCode", "Debit", "Credit"]}}
    folders = {"tb": tb_dir.as_posix()}
    naming = {"master_tb": "Master_TB_{period}.xlsx"}
    step = TBCollector(cfg, folders, naming, period="202301")

    io = step.plan_io()
    result = step.run(io)

    assert result.success
    master_path = Path(io.outputs["master_tb"])
    assert master_path.exists()
    rows = read_excel(master_path)
    assert len(rows) == 4
    assert result.metrics == {"files": 2, "rows": 4}
