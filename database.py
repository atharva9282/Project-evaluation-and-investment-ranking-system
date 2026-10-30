"""SQLite persistence for PEIRS."""
import json
import sqlite3
from pathlib import Path
from engine import DEFAULT_WEIGHTS

DB_PATH = Path(__file__).with_name("peirs.db")


def connect():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL, owner TEXT, sector TEXT,
                investment REAL NOT NULL, annual_revenue REAL NOT NULL,
                annual_cost REAL NOT NULL, years INTEGER NOT NULL,
                strategic REAL, technical REAL, impact REAL, timeline INTEGER,
                risk_probability INTEGER, risk_impact INTEGER, notes TEXT,
                npv REAL, irr REAL, roi REAL, bcr REAL, payback REAL,
                risk_score REAL, criteria TEXT, score REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        if not db.execute("SELECT 1 FROM settings WHERE key='weights'").fetchone():
            db.execute("INSERT INTO settings(key,value) VALUES('weights',?)", (json.dumps(DEFAULT_WEIGHTS),))


def get_weights():
    with connect() as db:
        row = db.execute("SELECT value FROM settings WHERE key='weights'").fetchone()
    return json.loads(row["value"]) if row else DEFAULT_WEIGHTS.copy()


def save_weights(weights):
    with connect() as db:
        db.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('weights',?)", (json.dumps(weights),))


def add_project(project, result):
    values = (
        project["name"], project.get("owner", ""), project.get("sector", "Other"),
        project["investment"], project["annual_revenue"], project["annual_cost"],
        project["years"], project["strategic"], project["technical"], project["impact"],
        project["timeline"], project["risk_probability"], project["risk_impact"],
        project.get("notes", ""), result["npv"], result["irr"], result["roi"],
        result["bcr"], result["payback"], result["risk_score"],
        json.dumps(result["criteria"]), result["score"]
    )
    with connect() as db:
        db.execute("""
            INSERT INTO projects(name,owner,sector,investment,annual_revenue,annual_cost,years,
            strategic,technical,impact,timeline,risk_probability,risk_impact,notes,npv,irr,roi,
            bcr,payback,risk_score,criteria,score)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, values)


def get_projects():
    with connect() as db:
        rows = db.execute("SELECT * FROM projects ORDER BY created_at DESC, id DESC").fetchall()
    projects = []
    for row in rows:
        item = dict(row)
        item["criteria"] = json.loads(item["criteria"] or "{}")
        projects.append(item)
    return projects


def get_project(project_id):
    with connect() as db:
        row = db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    if not row:
        return None
    item = dict(row)
    item["criteria"] = json.loads(item["criteria"] or "{}")
    return item


def load_demo_data():
    from engine import evaluate_project
    samples = [
        ("Campus Solar Grid", "Facilities", "Energy", 2400000, 850000, 260000, 8, 90, 85, 92, 18, 2, 3),
        ("Digital Learning Platform", "Academics", "Education", 1200000, 520000, 180000, 5, 95, 90, 88, 10, 2, 2),
        ("Smart Water Monitoring", "Operations", "Infrastructure", 900000, 360000, 140000, 5, 82, 80, 86, 9, 3, 3),
        ("Research Innovation Lab", "Research", "Technology", 3000000, 700000, 420000, 7, 88, 72, 95, 24, 3, 4),
        ("Community Health Kiosk", "Outreach", "Healthcare", 750000, 280000, 90000, 4, 78, 88, 94, 8, 2, 2),
    ]
    with connect() as db:
        if db.execute("SELECT COUNT(*) FROM projects").fetchone()[0]:
            return
    for name, owner, sector, inv, rev, cost, years, strategic, technical, impact, timeline, prob, risk in samples:
        project = {
            "name": name, "owner": owner, "sector": sector, "investment": inv,
            "annual_revenue": rev, "annual_cost": cost, "years": years,
            "strategic": strategic, "technical": technical, "impact": impact,
            "timeline": timeline, "risk_probability": prob, "risk_impact": risk, "notes": "Illustrative demo assumptions."
        }
        add_project(project, evaluate_project(project, get_weights()))
