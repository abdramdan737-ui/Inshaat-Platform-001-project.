import sqlite3
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path(__file__).resolve().parent / "users.sqlite3"

@contextmanager
def connection():
    con = sqlite3.connect(DB_PATH, timeout=20)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()

def init_db():
    with connection() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            display_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS login_attempts(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            attempted_at REAL NOT NULL,
            success INTEGER NOT NULL DEFAULT 0
        )""")

def get_user(email):
    with connection() as con:
        row = con.execute("SELECT * FROM users WHERE email=?", (email.lower().strip(),)).fetchone()
        return dict(row) if row else None

def create_user(email, display_name, password_hash):
    with connection() as con:
        con.execute(
            "INSERT INTO users(email,display_name,password_hash) VALUES(?,?,?)",
            (email.lower().strip(), display_name.strip(), password_hash),
        )

def record_attempt(email, timestamp, success):
    with connection() as con:
        con.execute(
            "INSERT INTO login_attempts(email,attempted_at,success) VALUES(?,?,?)",
            (email.lower().strip(), timestamp, int(success)),
        )

def recent_failures(email, since):
    with connection() as con:
        row = con.execute(
            "SELECT COUNT(*) AS n FROM login_attempts WHERE email=? AND attempted_at>? AND success=0",
            (email.lower().strip(), since),
        ).fetchone()
        return int(row["n"])
