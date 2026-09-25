import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
USE_POSTGRES = DATABASE_URL.startswith(("postgres://", "postgresql://"))
DB_PATH = Path(__file__).parent / "pixelworld.db"


def get_connection():
    if USE_POSTGRES:
        import psycopg
        from psycopg.rows import dict_row
        return psycopg.connect(DATABASE_URL, row_factory=dict_row)
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    return c


def q(sql):
    return sql.replace("?", "%s") if USE_POSTGRES else sql


def init_db():
    c = get_connection()

    c.execute(q("""CREATE TABLE IF NOT EXISTS pixels (
        x INTEGER NOT NULL,
        y INTEGER NOT NULL,
        color TEXT NOT NULL,
        username TEXT NOT NULL,
        discord_id TEXT,
        updated_at TEXT NOT NULL,
        PRIMARY KEY (x,y)
    )"""))

    c.execute(q("""CREATE TABLE IF NOT EXISTS auth_sessions (
        token_hash TEXT PRIMARY KEY,
        discord_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL
    )"""))

    c.execute(q("""CREATE TABLE IF NOT EXISTS players (
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
    )"""))

    c.execute(q("""CREATE TABLE IF NOT EXISTS redeemed_codes (
        code TEXT NOT NULL,
        discord_id TEXT NOT NULL,
        redeemed_at TEXT NOT NULL,
        PRIMARY KEY (code, discord_id)
    )"""))

    c.execute(q("""CREATE TABLE IF NOT EXISTS oauth_states (
        state TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL
    )"""))

    if not USE_POSTGRES:
        # Small migration for older SQLite databases.
        cols = {
            row[1]
            for row in c.execute("PRAGMA table_info(pixels)").fetchall()
        }

        if "discord_id" not in cols:
            c.execute(
                "ALTER TABLE pixels ADD COLUMN discord_id TEXT"
            )

        player_cols = {
            row[1]
            for row in c.execute("PRAGMA table_info(players)").fetchall()
        }

        required = {
            "discord_id",
            "username",
            "pixel_balance",
            "max_storage",
            "last_recharge_at",
            "cooldown_level",
            "storage_level",
            "crit_level",
            "total_placed",
            "skill_points_spent"
        }

        if player_cols and not required.issubset(player_cols):
            c.execute("DROP TABLE players")

            c.execute("""CREATE TABLE players (
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

    c.commit()
    c.close()


def now():
    return datetime.now(timezone.utc)


def get_all_pixels():
    c = get_connection()
    rows = c.execute(q("SELECT x,y,color,username,discord_id,updated_at FROM pixels")).fetchall()
    c.close()
    return [dict(r) for r in rows]


def get_pixel(x, y):
    c = get_connection()
    row = c.execute(q("SELECT x,y,color,username,discord_id,updated_at FROM pixels WHERE x=? AND y=?"), (x, y)).fetchone()
    c.close()
    return dict(row) if row else None


def get_player(discord_id, username):
    c = get_connection()
    row = c.execute(q("SELECT * FROM players WHERE discord_id=?"), (discord_id,)).fetchone()
    if not row:
        stamp = now().isoformat()
        c.execute(q("""INSERT INTO players(discord_id,username,pixel_balance,max_storage,last_recharge_at)
                      VALUES(?,?,?,?,?)"""), (discord_id, username, 20, 20, stamp))
        c.commit()
        row = c.execute(q("SELECT * FROM players WHERE discord_id=?"), (discord_id,)).fetchone()
    elif row["username"] != username:
        c.execute(q("UPDATE players SET username=? WHERE discord_id=?"), (username, discord_id))
        c.commit()
        row = c.execute(q("SELECT * FROM players WHERE discord_id=?"), (discord_id,)).fetchone()
    c.close()
    return dict(row)


def get_player_by_id(discord_id):
    c = get_connection()
    row = c.execute(q("SELECT * FROM players WHERE discord_id=?"), (discord_id,)).fetchone()
    c.close()
    return dict(row) if row else None


def update_player(discord_id, **values):
    if not values:
        return
    c = get_connection()
    keys = list(values.keys())
    c.execute(q(f"UPDATE players SET {', '.join(k + '=?' for k in keys)} WHERE discord_id=?"), [values[k] for k in keys] + [discord_id])
    c.commit()
    c.close()


def save_pixel(x, y, color, username, discord_id):
    """Save a pixel only if the cell is empty or already belongs to this Discord user."""
    stamp = now().isoformat()
    c = get_connection()
    if USE_POSTGRES:
        row = c.execute(q("""INSERT INTO pixels(x,y,color,username,discord_id,updated_at)
            VALUES(?,?,?,?,?,?)
            ON CONFLICT(x,y) DO UPDATE SET color=excluded.color,
            username=excluded.username,discord_id=excluded.discord_id,updated_at=excluded.updated_at
            WHERE pixels.discord_id = excluded.discord_id OR pixels.discord_id IS NULL
            RETURNING x"""), (x, y, color, username, discord_id, stamp)).fetchone()
    else:
        cur = c.execute(q("""INSERT INTO pixels(x,y,color,username,discord_id,updated_at)
            VALUES(?,?,?,?,?,?)
            ON CONFLICT(x,y) DO UPDATE SET color=excluded.color,
            username=excluded.username,discord_id=excluded.discord_id,updated_at=excluded.updated_at
            WHERE pixels.discord_id = excluded.discord_id OR pixels.discord_id IS NULL"""), (x, y, color, username, discord_id, stamp))
        row = cur.rowcount > 0
    c.commit()
    c.close()
    return bool(row)


def create_auth_session(token_hash, discord_id, expires_at):
    c = get_connection()
    c.execute(q("INSERT INTO auth_sessions(token_hash,discord_id,created_at,expires_at) VALUES(?,?,?,?)"), (token_hash, discord_id, now().isoformat(), expires_at))
    c.commit()
    c.close()


def get_auth_session(token_hash):
    c = get_connection()
    row = c.execute(q("SELECT * FROM auth_sessions WHERE token_hash=?"), (token_hash,)).fetchone()
    c.close()
    return dict(row) if row else None


def delete_auth_session(token_hash):
    c = get_connection()
    c.execute(q("DELETE FROM auth_sessions WHERE token_hash=?"), (token_hash,))
    c.commit()
    c.close()


def redeem_code(code, discord_id, pixels):
    """Redeem a code once per Discord account. Returns False when already redeemed."""
    c = get_connection()
    stamp = now().isoformat()
    try:
        c.execute(q("INSERT INTO redeemed_codes(code,discord_id,redeemed_at) VALUES(?,?,?)"), (code, discord_id, stamp))
    except Exception:
        c.rollback()
        c.close()
        return False
    c.execute(q("""UPDATE players SET pixel_balance =
                  CASE WHEN pixel_balance + ? > max_storage THEN max_storage
                       ELSE pixel_balance + ? END
                  WHERE discord_id=?"""), (pixels, pixels, discord_id))
    c.commit()
    c.close()
    return True


def create_oauth_state(state, expires_at):
    c = get_connection()

    # Supprime les anciens états expirés
    c.execute(
        q("DELETE FROM oauth_states WHERE expires_at <= ?"),
        (now().isoformat(),)
    )

    c.execute(
        q("""INSERT INTO oauth_states(state, created_at, expires_at)
             VALUES(?,?,?)"""),
        (state, now().isoformat(), expires_at)
    )

    c.commit()
    c.close()


def consume_oauth_state(state):
    c = get_connection()

    row = c.execute(
        q("SELECT expires_at FROM oauth_states WHERE state=?"),
        (state,)
    ).fetchone()

    if not row:
        c.close()
        return False

    expires_at = datetime.fromisoformat(row["expires_at"])

    if expires_at <= now():
        c.execute(
            q("DELETE FROM oauth_states WHERE state=?"),
            (state,)
        )
        c.commit()
        c.close()
        return False

    # Un state ne peut être utilisé qu'une seule fois
    c.execute(
        q("DELETE FROM oauth_states WHERE state=?"),
        (state,)
    )

    c.commit()
    c.close()

    return True
