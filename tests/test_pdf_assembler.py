from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from core.io_utils import write_excel
from plugins.pdf_assembler import PDFAssembler


def test_merges_generated_pdfs(tmp_path):
    tb_dir = tmp_path / "tb"
    fx_dir = tmp_path / "fx"
    support_dir = tmp_path / "support"
    tb_dir.mkdir(); fx_dir.mkdir(); support_dir.mkdir()

    write_excel([
        {"a": 1, "b": 2}
    ], tb_dir / "file1_202301.xlsx")
    write_excel([
        {"a": 3, "b": 4}
    ], fx_dir / "file2_202301.xlsx")

    cfg = {"params": {"include": ["{tb}/file1_{period}.xlsx", "{fx}/file2_{period}.xlsx"]}}
    folders = {"tb": tb_dir.as_posix(), "fx": fx_dir.as_posix(), "support": support_dir.as_posix()}
    naming = {"support_pdf": "Support_{period}.pdf"}
    step = PDFAssembler(cfg, folders, naming, period="202301")

    io = step.plan_io()
    result = step.run(io)

    assert result.success
    out_path = Path(io.outputs["support"])
    assert out_path.exists()
    content = out_path.read_text().strip()
    assert "1 | 2" in content and "3 | 4" in content
