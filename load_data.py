import sqlite3
import sys
from pathlib import Path

import pandas as pd

DB_PATH = "prices.db"
DEFAULT_CSV = "madurai banana.csv"
TEXT_COLS = ["Commodity", "District", "Grade", "Market", "State", "Variety"]
PRICE_COLS = ["Min_Price", "Max_Price", "Modal_Price"]
DB_COLS = ["Arrival_Date", "State", "District", "Market", "Commodity",
           "Variety", "Grade", "Min_Price", "Max_Price", "Modal_Price"]


def load_csv(csv_path):
    df = pd.read_csv(csv_path)

    for col in TEXT_COLS:
        df[col] = df[col].astype(str).str.strip()
    # fix names like "Anaiyur(Uzhavar Sandhai )" -> "Anaiyur(Uzhavar Sandhai)"
    df["Market"] = df["Market"].str.replace(r"\s+\)", ")", regex=True)

    # dates are day-first: 02/10/2026 means 2 October
    df["Arrival_Date"] = pd.to_datetime(df["Arrival_Date"], format="%d/%m/%Y")
    df["Arrival_Date"] = df["Arrival_Date"].dt.strftime("%Y-%m-%d")

    for col in PRICE_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["Modal_Price"])
    return df


def save_to_db(df, db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            Arrival_Date TEXT NOT NULL,
            State TEXT,
            District TEXT,
            Market TEXT NOT NULL,
            Commodity TEXT NOT NULL,
            Variety TEXT NOT NULL,
            Grade TEXT NOT NULL,
            Min_Price REAL,
            Max_Price REAL,
            Modal_Price REAL NOT NULL,
            UNIQUE (Arrival_Date, Market, Commodity, Variety, Grade)
        )
    """)
    before = conn.execute("SELECT COUNT(*) FROM prices").fetchone()[0]
    placeholders = ",".join("?" * len(DB_COLS))
    conn.executemany(
        f"INSERT OR IGNORE INTO prices ({','.join(DB_COLS)}) VALUES ({placeholders})",
        df[DB_COLS].values.tolist(),
    )
    conn.commit()
    after = conn.execute("SELECT COUNT(*) FROM prices").fetchone()[0]
    conn.close()
    return after - before


def main():
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(DEFAULT_CSV)
    if not csv_path.exists():
        sys.exit(f"File not found: {csv_path}")

    df = load_csv(csv_path)
    inserted = save_to_db(df)
    print(f"Rows read: {len(df)} | newly inserted: {inserted}")
    print(f"Date range: {df['Arrival_Date'].min()} to {df['Arrival_Date'].max()}")


if __name__ == "__main__":
    main()
    