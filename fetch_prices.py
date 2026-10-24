import argparse
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import quote, urlencode

import pandas as pd
import requests

API_URL = "https://api.data.gov.in/resource/35985678-0d79-46b4-9ed6-6f13308a1d24"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "application/json",
}
STATE = "Tamil Nadu"
DATA_FILE = Path("data") / "prices.csv"
SEED_FILE = Path("Madurai banana.csv")

COLUMNS = ["Arrival_Date", "Commodity", "Commodity_Code", "District", "Grade",
           "Market", "Max_Price", "Min_Price", "Modal_Price", "State", "Variety"]
KEY_COLS = ["Arrival_Date", "Market", "Commodity", "Variety", "Grade"]
TEXT_COLS = ["Commodity", "Commodity_Code", "District", "Grade", "Market",
             "State", "Variety"]
PRICE_COLS = ["Max_Price", "Min_Price", "Modal_Price"]
DATE_FORMATS = ["%d/%m/%Y", "%Y-%m-%d"]  # formats the date filter might accept


def get_page(params):
    """One API request with retries. Never prints the URL (it contains the key)."""
    for attempt in range(5):
        try:
            query = urlencode(params, quote_via=quote, safe="[]")
            resp = requests.get(f"{API_URL}?{query}", headers=HEADERS, timeout=45)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code in (401, 403):
                sys.exit(f"The API rejected the key (HTTP {resp.status_code}). "
                         "Check DATA_GOV_API_KEY.")
            if resp.status_code != 429 and resp.status_code < 500:
                print(f"  Request failed with HTTP {resp.status_code}; skipping.")
                return None
        except (requests.RequestException, ValueError) as err:
            print(f"  Network or JSON problem: {type(err).__name__}")
        wait = 2 ** attempt
        print(f"  Retrying in {wait}s...")
        time.sleep(wait)
    print("  Giving up on this request.")
    return None


def fetch_all(api_key, date_text, limit):
    """Fetch every page of Tamil Nadu records for one date."""
    records, offset = [], 0
    for _ in range(200):  # safety stop so we can never loop forever
        params = {
            "api-key": api_key,
            "format": "json",
            "offset": offset,
            "limit": limit,
            "filters[State]": STATE,
            "filters[Arrival_Date]": date_text,
        }
        data = get_page(params)
        if not data:
            break
        page = data.get("records") or []
        if not page:
            break
        records.extend(page)
        offset += len(page)
        try:
            total = int(data.get("total", 0) or 0)
        except (TypeError, ValueError):
            total = 0
        if total and offset >= total:
            break
        time.sleep(0.5)
    return records


def fetch_day(api_key, day, limit):
    for fmt in DATE_FORMATS:
        records = fetch_all(api_key, day.strftime(fmt), limit)
        if records:
            return records
    return []


def pick(rec, *names):
    for name in names:
        if name in rec and rec[name] is not None:
            return rec[name]
    return ""


def to_row(record):
    r = {str(k).lower(): v for k, v in record.items()}
    return {
        "Arrival_Date": pick(r, "arrival_date"),
        "Commodity": pick(r, "commodity"),
        "Commodity_Code": pick(r, "commodity_code"),
        "District": pick(r, "district"),
        "Grade": pick(r, "grade"),
        "Market": pick(r, "market"),
        "Max_Price": pick(r, "max_price", "max_x0020_price"),
        "Min_Price": pick(r, "min_price", "min_x0020_price"),
        "Modal_Price": pick(r, "modal_price", "modal_x0020_price"),
        "State": pick(r, "state"),
        "Variety": pick(r, "variety"),
    }


def parse_dates(series):
    text = series.astype(str).str.strip()
    parsed = pd.to_datetime(text, format="%d/%m/%Y", errors="coerce")
    return parsed.fillna(pd.to_datetime(text, format="%Y-%m-%d", errors="coerce"))


def normalise(df):
    df = df[COLUMNS].copy()
    for col in TEXT_COLS:
        df[col] = df[col].fillna("").astype(str).str.strip()
    df["Market"] = df["Market"].str.replace(r"\s+\)", ")", regex=True)
    df["Arrival_Date"] = parse_dates(df["Arrival_Date"])
    for col in PRICE_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.dropna(subset=["Arrival_Date", "Modal_Price"])


def main():
    parser = argparse.ArgumentParser(description="Fetch Tamil Nadu mandi prices.")
    parser.add_argument("--days", type=int, default=3, help="how many recent days to fetch")
    parser.add_argument("--limit", type=int, default=500, help="records per request")
    parser.add_argument("--keep-days", type=int, default=90, help="how many days of history to keep")
    args = parser.parse_args()

    api_key = os.environ.get("DATA_GOV_API_KEY")
    if not api_key:
        sys.exit("DATA_GOV_API_KEY is not set in this window.")

    if DATA_FILE.exists():
        existing = pd.read_csv(DATA_FILE, dtype=str)
    elif SEED_FILE.exists():
        existing = pd.read_csv(SEED_FILE, dtype=str)
    else:
        existing = pd.DataFrame(columns=COLUMNS)
    existing = normalise(existing).drop_duplicates(subset=KEY_COLS, keep="last")

    rows, shown_fields = [], False
    today = date.today()
    for i in range(args.days):
        day = today - timedelta(days=i)
        records = fetch_day(api_key, day, args.limit)
        print(f"{day.isoformat()}: {len(records)} records")
        if records and not shown_fields:
            print("Fields in the API response:", sorted(records[0].keys()))
            shown_fields = True
        rows.extend(to_row(r) for r in records)
        time.sleep(0.5)

    if not rows:
        print("No records fetched. Try --limit 100, or tell me what was printed above.")
        return

    fetched = normalise(pd.DataFrame(rows, columns=COLUMNS))
    combined = pd.concat([existing, fetched], ignore_index=True)
    combined = combined.drop_duplicates(subset=KEY_COLS, keep="last")
    new_count = len(combined) - len(existing)

    cutoff = pd.Timestamp(today) - pd.Timedelta(days=args.keep_days)
    combined = combined[combined["Arrival_Date"] >= cutoff]
    combined = combined.sort_values(["Arrival_Date", "District", "Market", "Commodity", "Variety"])
    combined["Arrival_Date"] = combined["Arrival_Date"].dt.strftime("%d/%m/%Y")

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(DATA_FILE, index=False, float_format="%.10g")
    print(f"Fetched {len(fetched)} rows | new: {new_count} | total in file: {len(combined)}")


if __name__ == "__main__":
    main()