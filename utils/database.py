import aiosqlite
import os
import time

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "bot.db")


async def init_db():
    """Initialise toutes les tables SQLite au démarrage."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_levels (
                guild_id       INTEGER NOT NULL,
                user_id        INTEGER NOT NULL,
                xp             INTEGER DEFAULT 0,
                level          INTEGER DEFAULT 0,
                last_xp_time   REAL    DEFAULT 0,
                messages_count INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reaction_roles (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id   INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                emoji      TEXT    NOT NULL,
                role_id    INTEGER NOT NULL,
                UNIQUE (message_id, emoji)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS announcements (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                type     TEXT    NOT NULL,
                last_id  TEXT,
                guild_id INTEGER NOT NULL,
                UNIQUE (type, guild_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS warnings (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id     INTEGER NOT NULL,
                user_id      INTEGER NOT NULL,
                reason       TEXT,
                moderator_id INTEGER,
                timestamp    REAL    NOT NULL,
                active       INTEGER DEFAULT 1
            )
        """)
        await db.commit()


# ─── XP / Niveaux ─────────────────────────────────────────────────────────────

async def get_user_xp(guild_id: int, user_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT xp, level, last_xp_time, messages_count "
            "FROM user_levels WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        ) as cur:
            row = await cur.fetchone()
    if row:
        return {"xp": row[0], "level": row[1], "last_xp_time": row[2], "messages_count": row[3]}
    return {"xp": 0, "level": 0, "last_xp_time": 0.0, "messages_count": 0}


async def update_user_xp(
    guild_id: int,
    user_id: int,
    xp: int,
    level: int,
    last_xp_time: float,
    messages_count: int,
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO user_levels (guild_id, user_id, xp, level, last_xp_time, messages_count)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET
                xp             = excluded.xp,
                level          = excluded.level,
                last_xp_time   = excluded.last_xp_time,
                messages_count = excluded.messages_count
            """,
            (guild_id, user_id, xp, level, last_xp_time, messages_count),
        )
        await db.commit()


async def get_leaderboard(guild_id: int, limit: int = 10) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id, xp, level FROM user_levels "
            "WHERE guild_id = ? ORDER BY xp DESC LIMIT ?",
            (guild_id, limit),
        ) as cur:
            return await cur.fetchall()


# ─── Reaction roles ───────────────────────────────────────────────────────────

async def add_reaction_role(
    guild_id: int, channel_id: int, message_id: int, emoji: str, role_id: int
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO reaction_roles (guild_id, channel_id, message_id, emoji, role_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (guild_id, channel_id, message_id, emoji, role_id),
        )
        await db.commit()


async def get_reaction_role(message_id: int, emoji: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT role_id, guild_id FROM reaction_roles WHERE message_id = ? AND emoji = ?",
            (message_id, emoji),
        ) as cur:
            row = await cur.fetchone()
    return {"role_id": row[0], "guild_id": row[1]} if row else None


async def get_all_reaction_roles(guild_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT channel_id, message_id, emoji, role_id FROM reaction_roles WHERE guild_id = ?",
            (guild_id,),
        ) as cur:
            return await cur.fetchall()


async def remove_reaction_role(message_id: int, emoji: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM reaction_roles WHERE message_id = ? AND emoji = ?",
            (message_id, emoji),
        )
        await db.commit()


# ─── Annonces YouTube / Twitch ────────────────────────────────────────────────

async def get_last_announcement(guild_id: int, announcement_type: str) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT last_id FROM announcements WHERE type = ? AND guild_id = ?",
            (announcement_type, guild_id),
        ) as cur:
            row = await cur.fetchone()
    return row[0] if row else None


async def update_last_announcement(guild_id: int, announcement_type: str, last_id: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO announcements (type, last_id, guild_id) VALUES (?, ?, ?)
            ON CONFLICT(type, guild_id) DO UPDATE SET last_id = excluded.last_id
            """,
            (announcement_type, last_id, guild_id),
        )
        await db.commit()


# ─── Avertissements ───────────────────────────────────────────────────────────

async def add_warning(guild_id: int, user_id: int, reason: str, moderator_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO warnings (guild_id, user_id, reason, moderator_id, timestamp) "
            "VALUES (?, ?, ?, ?, ?)",
            (guild_id, user_id, reason, moderator_id, time.time()),
        )
        await db.commit()


async def get_warnings(guild_id: int, user_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, reason, moderator_id, timestamp FROM warnings "
            "WHERE guild_id = ? AND user_id = ? AND active = 1 ORDER BY timestamp DESC",
            (guild_id, user_id),
        ) as cur:
            return await cur.fetchall()


async def clear_warnings(guild_id: int, user_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE warnings SET active = 0 WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        await db.commit()
