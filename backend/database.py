import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(__file__).parent / "pixelworld.db"

def get_connection():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = get_connection()
    c.execute("""CREATE TABLE IF NOT EXISTS pixels (
        x INTEGER NOT NULL,
        y INTEGER NOT NULL,
        color TEXT NOT NULL,
        username TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        PRIMARY KEY (x,y)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS players (
        username TEXT PRIMARY KEY,
        last_pixel_at TEXT
    )""")
    c.commit()
    c.close()

def get_all_pixels():
    c=get_connection()
    rows=c.execute("SELECT x,y,color,username,updated_at FROM pixels").fetchall()
    c.close()
    return [dict(r) for r in rows]

def get_last_pixel(username):
    c=get_connection()
    row=c.execute("SELECT last_pixel_at FROM players WHERE username=?",(username,)).fetchone()
    c.close()
    return datetime.fromisoformat(row["last_pixel_at"]) if row and row["last_pixel_at"] else None

def save_pixel(x,y,color,username):
    now=datetime.now(timezone.utc)
    c=get_connection()
    c.execute("""INSERT INTO players(username,last_pixel_at) VALUES(?,?)
        ON CONFLICT(username) DO UPDATE SET last_pixel_at=excluded.last_pixel_at""",
        (username,now.isoformat()))
    c.execute("""INSERT INTO pixels(x,y,color,username,updated_at) VALUES(?,?,?,?,?)
        ON CONFLICT(x,y) DO UPDATE SET color=excluded.color,
        username=excluded.username,updated_at=excluded.updated_at""",
        (x,y,color,username,now.isoformat()))
    c.commit()
    c.close()
