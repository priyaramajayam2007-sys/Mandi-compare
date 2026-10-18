import sqlite3

from flask import Flask, render_template, request

app = Flask(__name__)
DB_PATH = "prices.db"


def query(sql, params=()):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def pick(value, options):
    """Use the chosen value only if it is really in the list."""
    return value if value in options else (options[0] if options else None)


@app.route("/")
def home():
    commodities = [r["Commodity"] for r in query(
        "SELECT DISTINCT Commodity FROM prices ORDER BY Commodity")]
    if not commodities:
        return render_template("index.html", commodities=[])

    commodity = pick(request.args.get("commodity"), commodities)

    varieties = [r["Variety"] for r in query(
        "SELECT DISTINCT Variety FROM prices WHERE Commodity = ? ORDER BY Variety",
        (commodity,))]
    variety = pick(request.args.get("variety"), varieties)

    grades = [r["Grade"] for r in query(
        "SELECT DISTINCT Grade FROM prices WHERE Commodity = ? AND Variety = ? ORDER BY Grade",
        (commodity, variety))]
    grade = pick(request.args.get("grade"), grades)

    # newest price reported by each market
    latest = query(
        """
        SELECT Market, Arrival_Date, Min_Price, Modal_Price, Max_Price
        FROM prices p
        WHERE Commodity = ? AND Variety = ? AND Grade = ?
          AND Arrival_Date = (
              SELECT MAX(Arrival_Date) FROM prices
              WHERE Market = p.Market AND Commodity = p.Commodity
                AND Variety = p.Variety AND Grade = p.Grade)
        ORDER BY Modal_Price DESC
        """,
        (commodity, variety, grade))

    last_updated = query("SELECT MAX(Arrival_Date) AS d FROM prices")[0]["d"]

    return render_template(
        "index.html",
        commodities=commodities, varieties=varieties, grades=grades,
        commodity=commodity, variety=variety, grade=grade,
        latest=latest, last_updated=last_updated)


if __name__ == "__main__":
    app.run(debug=True)