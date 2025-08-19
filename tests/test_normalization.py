import pytest

pd = pytest.importorskip("pandas")

from core import normalization as norm


def test_resolve_and_coerce(tmp_path):
    data = {
        "Entity": ["US1"],
        "Account": ["1000"],
        "Debit Amount": ["100"],
        "Credit Amount": [50],
        "FiscalPeriod": ["2025-01"],
        "Currency": ["usd"],
    }
    df = pd.DataFrame(data)
    df = norm.resolve_columns(df, norm.SCHEMAS["TB"], norm.COLUMN_ALIASES)
    df = norm.coerce_tb_types(df)
    assert set(norm.SCHEMAS["TB"]).issubset(df.columns)
    assert df["Debit"].iloc[0] == 100.0
    assert df["Credit"].iloc[0] == 50.0
    assert df["Period"].iloc[0] == "202501"
    assert df["CurrencyCode"].iloc[0] == "USD"


def test_filename_inference():
    assert norm.infer_period_from_filename("TB_USA_202501.xlsx") == "202501"
    assert norm.infer_entity_from_filename("TB_GBR_Q1_2025.xlsx") == "GBR"


def test_load_fx_rates(tmp_path):
    df = pd.DataFrame(
        {
            "ISO Currency": ["eur"],
            "FX": [1.2],
            "Period": ["202501"],
            "Source": ["manual"],
        }
    )
    path = tmp_path / "fx.xlsx"
    df.to_excel(path, index=False)
    rates = norm.load_fx_rates(str(path))
    assert rates["EUR"] == 1.2
