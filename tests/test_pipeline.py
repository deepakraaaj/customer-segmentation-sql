import duckdb
import pandas as pd
import pytest

from src.segment import rfm_scores
from src.sql_runner import build_sales, query

ROWS = [
    # invoice, stock_code, description, quantity, invoice_date, price, customer_id, country
    ("1001", "22423", "CAKESTAND", 2, "2011-01-10 10:00", 10.0, 1.0, "UK"),        # kept
    ("1001", "22423", "CAKESTAND", 2, "2011-01-10 10:00", 10.0, 1.0, "UK"),        # exact duplicate -> dropped
    ("C1002", "22423", "CAKESTAND", -1, "2011-01-11 10:00", 10.0, 1.0, "UK"),      # cancellation -> dropped
    ("1003", "85123A", "T-LIGHT", 0, "2011-01-12 10:00", 3.0, 2.0, "UK"),          # zero quantity -> dropped
    ("1004", "85123A", "T-LIGHT", 5, "2011-01-12 10:00", 0.0, 2.0, "UK"),          # zero price -> dropped
    ("1005", "85123A", "T-LIGHT", 5, "2011-01-12 10:00", 3.0, None, "UK"),         # no customer -> dropped
    ("1006", "POST", "POSTAGE", 1, "2011-01-12 10:00", 18.0, 2.0, "France"),       # non-product code -> dropped
    ("1007", "85123A", "T-LIGHT", 4, "2011-02-01 09:00", 2.5, 2.0, "France"),      # kept
    ("1008", "85123A", "T-LIGHT", 1, "2011-03-01 09:00", 2.5, 2.0, "France"),      # kept
]


@pytest.fixture()
def con():
    raw = pd.DataFrame(ROWS, columns=["invoice", "stock_code", "description", "quantity",
                                      "invoice_date", "price", "customer_id", "country"])
    raw["invoice_date"] = pd.to_datetime(raw["invoice_date"])
    c = duckdb.connect()
    c.register("raw", raw)
    build_sales(c)
    return c


def test_cleaning_rules_keep_only_valid_product_sales(con):
    sales = con.sql("SELECT invoice, revenue FROM sales ORDER BY invoice").df()
    assert sales["invoice"].tolist() == ["1001", "1007", "1008"]
    assert sales["revenue"].tolist() == [20.0, 10.0, 2.5]


def test_rfm_values(con):
    rfm = query(con, "07_rfm").set_index("customer_id")
    # snapshot = last purchase (2011-03-01) + 1 day
    assert rfm.loc[1, "recency_days"] == 51
    assert rfm.loc[2, "recency_days"] == 1
    assert rfm.loc[2, "frequency"] == 2
    assert rfm.loc[2, "monetary"] == 12.5


def test_cohort_retention_starts_at_100(con):
    cohorts = query(con, "06_cohort_retention")
    assert (cohorts.loc[cohorts["month_number"] == 0, "retention_pct"] == 100).all()


def test_rfm_scores_reward_recent_frequent_big_spenders():
    rfm = pd.DataFrame({"customer_id": range(10), "recency_days": range(1, 11),
                        "frequency": range(10, 0, -1), "monetary": range(1000, 0, -100)})
    scored = rfm_scores(rfm).set_index("customer_id")
    assert scored.loc[0, "RFM_score"] == "555"
    assert scored.loc[9, "RFM_score"] == "111"
