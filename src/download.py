"""Download UCI Online Retail II and cache it as Parquet in data/.

Usage: python -m src.download
"""
import io
import zipfile
from pathlib import Path
from urllib.request import urlopen

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RAW_PARQUET = DATA_DIR / "online_retail_ii.parquet"
URL = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"


def download() -> Path:
    if RAW_PARQUET.exists():
        return RAW_PARQUET
    DATA_DIR.mkdir(exist_ok=True)
    xlsx = DATA_DIR / "online_retail_II.xlsx"
    if not xlsx.exists():
        print(f"Downloading {URL} ...")
        with zipfile.ZipFile(io.BytesIO(urlopen(URL).read())) as zf:
            zf.extract("online_retail_II.xlsx", DATA_DIR)
    print("Converting both Excel sheets (2009-10, 2010-11) to Parquet, this takes a few minutes ...")
    df = pd.concat(pd.read_excel(xlsx, sheet_name=None, dtype={"Invoice": str, "StockCode": str}).values(),
                   ignore_index=True)
    df.columns = ["invoice", "stock_code", "description", "quantity", "invoice_date", "price", "customer_id", "country"]
    duckdb.sql(f"COPY (SELECT * FROM df) TO '{RAW_PARQUET}' (FORMAT PARQUET)")
    print(f"Saved {len(df):,} rows to {RAW_PARQUET}")
    return RAW_PARQUET


if __name__ == "__main__":
    download()
