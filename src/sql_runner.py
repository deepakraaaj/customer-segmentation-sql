"""Run the SQL layer in DuckDB and save every query result to reports/sql/.

Usage: python -m src.sql_runner
"""
from pathlib import Path

import duckdb
import pandas as pd

from src.download import RAW_PARQUET, ROOT, download

SQL_DIR = ROOT / "sql"
OUT_DIR = ROOT / "reports" / "sql"


def connect(parquet: Path = RAW_PARQUET) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute(f"CREATE VIEW raw AS SELECT * FROM read_parquet('{parquet}')")
    return con


def build_sales(con: duckdb.DuckDBPyConnection) -> None:
    """Create the cleaned `sales` table from whatever `raw` view/table the connection has."""
    con.execute((SQL_DIR / "01_clean.sql").read_text())


def query(con: duckdb.DuckDBPyConnection, name: str) -> pd.DataFrame:
    """Run one analysis query, e.g. query(con, '07_rfm')."""
    return con.sql((SQL_DIR / f"{name}.sql").read_text()).df()


def run_all() -> dict[str, pd.DataFrame]:
    download()
    con = connect()
    build_sales(con)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results = {}
    for path in sorted(SQL_DIR.glob("*.sql"))[1:]:  # 01_clean.sql is DDL, the rest are SELECTs
        df = query(con, path.stem)
        df.to_csv(OUT_DIR / f"{path.stem}.csv", index=False)
        results[path.stem] = df
        print(f"{path.name:28s} -> {len(df):>6,} rows")
    return results


if __name__ == "__main__":
    run_all()
