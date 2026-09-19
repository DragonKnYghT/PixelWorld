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
        discord_id TEXT,
        updated_at TEXT NOT NULL,
        PRIMARY KEY (x,y)
    )""")
    # Migration for an older PixelWorld database.
    cols = {row[1] for row in c.execute("PRAGMA table_info(pixels)").fetchall()}
    if "discord_id" not in cols:
        c.execute("ALTER TABLE pixels ADD COLUMN discord_id TEXT")

    c.execute("""CREATE TABLE IF NOT EXISTS auth_sessions (
        token_hash TEXT PRIMARY KEY,
        discord_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS players (
        discord_id TEXT PRIMARY KEY,
        username TEXT NOT NULL,
        pixel_balance INTEGER NOT NULL DEFAULT 20,
        max_storage INTEGER NOT NULL DEFAULT 20,
        last_recharge_at TEXT NOT NULL,
        cooldown_level INTEGER NOT NULL DEFAULT 0,
        storage_level INTEGER NOT NULL DEFAULT 0,
        crit_level INTEGER NOT NULL DEFAULT 0,
        total_placed INTEGER NOT NULL DEFAULT 0,
        skill_points_spent INTEGER NOT NULL DEFAULT 0
    )""")
    player_cols = {row[1] for row in c.execute("PRAGMA table_info(players)").fetchall()}
    required = {"discord_id","username","pixel_balance","max_storage","last_recharge_at","cooldown_level","storage_level","crit_level","total_placed","skill_points_spent"}
    if player_cols and not required.issubset(player_cols):
        # Migrate the original V1 players table (username + last_pixel_at) to the Discord-based schema.
        old_rows = c.execute("SELECT username, last_pixel_at FROM players").fetchall() if "username" in player_cols else []
        c.execute("DROP TABLE players")
        c.execute("""CREATE TABLE players (
            discord_id TEXT PRIMARY KEY, username TEXT NOT NULL,
            pixel_balance INTEGER NOT NULL DEFAULT 20, max_storage INTEGER NOT NULL DEFAULT 20,
            last_recharge_at TEXT NOT NULL, cooldown_level INTEGER NOT NULL DEFAULT 0,
            storage_level INTEGER NOT NULL DEFAULT 0, crit_level INTEGER NOT NULL DEFAULT 0,
            total_placed INTEGER NOT NULL DEFAULT 0, skill_points_spent INTEGER NOT NULL DEFAULT 0
        )""")
        # Old anonymous names cannot safely be linked to Discord accounts, so they are intentionally not copied.
    c.commit()
    c.close()


def now():
    return datetime.now(timezone.utc)


def get_all_pixels():
    c = get_connection()
    rows = c.execute("SELECT x,y,color,username,discord_id,updated_at FROM pixels").fetchall()
    c.close()
    return [dict(r) for r in rows]


def get_pixel(x, y):
    c = get_connection()
    row = c.execute(
        "SELECT x,y,color,username,discord_id,updated_at FROM pixels WHERE x=? AND y=?",
        (x, y),
    ).fetchone()
    c.close()
    return dict(row) if row else None


def get_player(discord_id, username):
    c = get_connection()
    row = c.execute("SELECT * FROM players WHERE discord_id=?", (discord_id,)).fetchone()
    if not row:
        stamp = now().isoformat()
        c.execute(
            """INSERT INTO players(discord_id,username,pixel_balance,max_storage,last_recharge_at)
               VALUES(?,?,?,?,?)""",
            (discord_id, username, 20, 20, stamp),
        )
        c.commit()
        row = c.execute("SELECT * FROM players WHERE discord_id=?", (discord_id,)).fetchone()
    elif row["username"] != username:
        c.execute("UPDATE players SET username=? WHERE discord_id=?", (username, discord_id))
        c.commit()
        row = c.execute("SELECT * FROM players WHERE discord_id=?", (discord_id,)).fetchone()
    c.close()
    return dict(row)


def get_player_by_id(discord_id):
    c = get_connection()
    row = c.execute("SELECT * FROM players WHERE discord_id=?", (discord_id,)).fetchone()
    c.close()
    return dict(row) if row else None


def update_player(discord_id, **values):
    if not values:
        return
    c = get_connection()
    keys = list(values.keys())
    c.execute(
        f"UPDATE players SET {', '.join(k + '=?' for k in keys)} WHERE discord_id=?",
        [values[k] for k in keys] + [discord_id],
    )
    c.commit()
    c.close()


def save_pixel(x, y, color, username, discord_id):
    stamp = now().isoformat()
    c = get_connection()
    c.execute(
        """INSERT INTO pixels(x,y,color,username,discord_id,updated_at) VALUES(?,?,?,?,?,?)
           ON CONFLICT(x,y) DO UPDATE SET color=excluded.color,
           username=excluded.username,discord_id=excluded.discord_id,updated_at=excluded.updated_at""",
        (x, y, color, username, discord_id, stamp),
    )
    c.commit()
    c.close()


def create_auth_session(token_hash, discord_id, expires_at):
    c = get_connection()
    c.execute("INSERT INTO auth_sessions(token_hash,discord_id,created_at,expires_at) VALUES(?,?,?,?)", (token_hash, discord_id, now().isoformat(), expires_at))
    c.commit()
    c.close()


def get_auth_session(token_hash):
    c = get_connection()
    row = c.execute("SELECT * FROM auth_sessions WHERE token_hash=?", (token_hash,)).fetchone()
    c.close()
    return dict(row) if row else None


def delete_auth_session(token_hash):
    c = get_connection()
    c.execute("DELETE FROM auth_sessions WHERE token_hash=?", (token_hash,))
    c.commit()
    c.close()
