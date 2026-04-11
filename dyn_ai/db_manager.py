"""
Database Manager - SQLite persistence layer for Live AI Tuner

Schema
------
race_sessions (MODIFIED: no user data)
    One row per detected raceresults.txt change.
    Stores track identity and AIW ratios only.

session_ai_results
    One row per AI driver per session.
    Stores name, vehicle, team, qualifying time, race best lap, race time,
    and laps completed.

ratio_updates
    Audit log of every AIW file write.

aiw_path_cache
    Persistent equivalent of the in-memory AIW path dict.

curve_points / curve_params / curve_globals
    Replaces global_curve.json.
"""

import sqlite3
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Tuple, Dict

logger = logging.getLogger(__name__)

# ── Schema ─────────────────────────────────────────────────────────────────────

_DDL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS race_sessions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp           TEXT    NOT NULL,
    track_name          TEXT,
    track_folder        TEXT,
    aiw_file            TEXT,
    qual_ratio          REAL,
    race_ratio          REAL
    -- No user data stored here
);

CREATE TABLE IF NOT EXISTS session_ai_results (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER NOT NULL REFERENCES race_sessions(id) ON DELETE CASCADE,
    name            TEXT,
    vehicle         TEXT,
    team            TEXT,
    qual_time       TEXT,
    qual_time_sec   REAL,
    best_lap        TEXT,
    best_lap_sec    REAL,
    race_time       TEXT,
    race_time_sec   REAL,
    laps            INTEGER
);

CREATE INDEX IF NOT EXISTS idx_ai_session ON session_ai_results(session_id);
CREATE INDEX IF NOT EXISTS idx_ai_name    ON session_ai_results(name);
CREATE INDEX IF NOT EXISTS idx_ai_vehicle ON session_ai_results(vehicle);

CREATE TABLE IF NOT EXISTS ratio_updates (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT    NOT NULL,
    track_name  TEXT,
    aiw_path    TEXT,
    ratio_type  TEXT,
    old_value   REAL,
    new_value   REAL,
    success     INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS aiw_path_cache (
    cache_key   TEXT PRIMARY KEY,
    aiw_path    TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS curve_points (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    track_name  TEXT NOT NULL,
    ratio       REAL NOT NULL,
    midpoint    REAL NOT NULL,
    added_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS curve_params (
    track_name  TEXT PRIMARY KEY,
    a           REAL NOT NULL,
    b           REAL NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS curve_globals (
    key     TEXT PRIMARY KEY,
    value   REAL NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Database class ─────────────────────────────────────────────────────────────

class Database:
    """Thread-safe SQLite wrapper (WAL mode)."""

    def __init__(self, db_path: str = "live_ai_tuner.db"):
        self.db_path = str(db_path)
        self._init_schema()

    def _init_schema(self):
        with self._connect() as con:
            con.executescript(_DDL)
        logger.info(f"Database ready: {self.db_path}")

    @contextmanager
    def _connect(self):
        con = sqlite3.connect(self.db_path, check_same_thread=False)
        con.row_factory = sqlite3.Row
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    # ── Race sessions (NO USER DATA) ───────────────────────────────────────────

    def save_race_session(self, data: dict) -> Optional[int]:
        """
        Persist a parsed race result - NO USER DATA.

        ``data`` is the dict produced by ``RaceResults.to_dict()``.
        Only track identity and AIW ratios are stored.
        Every AI result goes into session_ai_results (one row each).
        Returns the new session id, or None on failure.
        """
        session_sql = """
            INSERT INTO race_sessions (
                timestamp,
                track_name, track_folder, aiw_file,
                qual_ratio, race_ratio
            ) VALUES (
                :timestamp,
                :track_name, :track_folder, :aiw_file,
                :qual_ratio, :race_ratio
            )
        """

        ai_sql = """
            INSERT INTO session_ai_results (
                session_id,
                name, vehicle, team,
                qual_time, qual_time_sec,
                best_lap, best_lap_sec,
                race_time, race_time_sec,
                laps
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        try:
            with self._connect() as con:
                session_row = {
                    "timestamp":            _now(),
                    "track_name":           data.get("track_name"),
                    "track_folder":         data.get("track_folder"),
                    "aiw_file":             data.get("aiw_file"),
                    "qual_ratio":           data.get("qual_ratio"),
                    "race_ratio":           data.get("race_ratio"),
                }
                cur = con.execute(session_sql, session_row)
                session_id = cur.lastrowid

                for ai in data.get("ai_results", []):
                    con.execute(ai_sql, (
                        session_id,
                        ai.get("name"),
                        ai.get("vehicle"),
                        ai.get("team"),
                        ai.get("qual_time"),
                        ai.get("qual_time_sec"),
                        ai.get("best_lap"),
                        ai.get("best_lap_sec"),
                        ai.get("race_time"),
                        ai.get("race_time_sec"),
                        ai.get("laps"),
                    ))

            logger.info(
                f"Saved session #{session_id} — {data.get('track_name')} "
                f"({len(data.get('ai_results', []))} AI drivers)"
            )
            return session_id

        except Exception as e:
            logger.error(f"Error saving race session: {e}")
            return None

    def get_sessions_for_track(self, track_name: str) -> List[sqlite3.Row]:
        with self._connect() as con:
            return con.execute(
                "SELECT * FROM race_sessions WHERE track_name = ? ORDER BY timestamp DESC",
                (track_name,),
            ).fetchall()

    def get_recent_sessions(self, limit: int = 50) -> List[sqlite3.Row]:
        with self._connect() as con:
            return con.execute(
                "SELECT * FROM race_sessions ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()

    def get_ai_results_for_session(self, session_id: int) -> List[sqlite3.Row]:
        """All AI rows for a session, ordered fastest race lap first."""
        with self._connect() as con:
            return con.execute(
                """SELECT * FROM session_ai_results
                   WHERE session_id = ?
                   ORDER BY best_lap_sec ASC""",
                (session_id,),
            ).fetchall()

    def get_ai_results_for_track(self, track_name: str) -> List[sqlite3.Row]:
        """All AI results ever recorded at a track, with session metadata."""
        with self._connect() as con:
            return con.execute(
                """SELECT ai.*, rs.timestamp, rs.qual_ratio, rs.race_ratio
                   FROM session_ai_results ai
                   JOIN race_sessions rs ON rs.id = ai.session_id
                   WHERE rs.track_name = ?
                   ORDER BY rs.timestamp DESC, ai.best_lap_sec ASC""",
                (track_name,),
            ).fetchall()

    # ── Ratio updates ──────────────────────────────────────────────────────────

    def log_ratio_update(
        self,
        track_name: str,
        aiw_path: str,
        ratio_type: str,
        old_value: Optional[float],
        new_value: float,
        success: bool,
    ) -> None:
        try:
            with self._connect() as con:
                con.execute(
                    """INSERT INTO ratio_updates
                           (timestamp, track_name, aiw_path, ratio_type, old_value, new_value, success)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (_now(), track_name, str(aiw_path), ratio_type, old_value, new_value, int(success)),
                )
        except Exception as e:
            logger.error(f"Error logging ratio update: {e}")

    def get_ratio_history(
        self, track_name: str, ratio_type: Optional[str] = None, limit: int = 100
    ) -> List[sqlite3.Row]:
        with self._connect() as con:
            if ratio_type:
                return con.execute(
                    """SELECT * FROM ratio_updates
                       WHERE track_name = ? AND ratio_type = ?
                       ORDER BY timestamp DESC LIMIT ?""",
                    (track_name, ratio_type, limit),
                ).fetchall()
            return con.execute(
                "SELECT * FROM ratio_updates WHERE track_name = ? ORDER BY timestamp DESC LIMIT ?",
                (track_name, limit),
            ).fetchall()

    # ── AIW path cache ─────────────────────────────────────────────────────────

    def get_cached_aiw_path(self, cache_key: str) -> Optional[str]:
        with self._connect() as con:
            row = con.execute(
                "SELECT aiw_path FROM aiw_path_cache WHERE cache_key = ?", (cache_key,)
            ).fetchone()
        return row["aiw_path"] if row else None

    def set_cached_aiw_path(self, cache_key: str, aiw_path: str) -> None:
        try:
            with self._connect() as con:
                con.execute(
                    """INSERT INTO aiw_path_cache (cache_key, aiw_path, updated_at)
                       VALUES (?, ?, ?)
                       ON CONFLICT(cache_key) DO UPDATE
                           SET aiw_path=excluded.aiw_path, updated_at=excluded.updated_at""",
                    (cache_key, str(aiw_path), _now()),
                )
        except Exception as e:
            logger.error(f"Error caching AIW path: {e}")

    def invalidate_aiw_cache(self, cache_key: str) -> None:
        with self._connect() as con:
            con.execute("DELETE FROM aiw_path_cache WHERE cache_key = ?", (cache_key,))

    # ── Curve data ─────────────────────────────────────────────────────────────

    def save_curve_point(self, track_name: str, ratio: float, midpoint: float) -> None:
        try:
            with self._connect() as con:
                con.execute(
                    "INSERT INTO curve_points (track_name, ratio, midpoint, added_at) VALUES (?, ?, ?, ?)",
                    (track_name, ratio, midpoint, _now()),
                )
        except Exception as e:
            logger.error(f"Error saving curve point: {e}")

    def get_curve_points(self, track_name: str) -> List[Tuple[float, float]]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT ratio, midpoint FROM curve_points WHERE track_name = ? ORDER BY ratio",
                (track_name,),
            ).fetchall()
        return [(r["ratio"], r["midpoint"]) for r in rows]

    def get_all_curve_points(self) -> Dict[str, List[Tuple[float, float]]]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT track_name, ratio, midpoint FROM curve_points ORDER BY track_name, ratio"
            ).fetchall()
        result: Dict[str, List[Tuple[float, float]]] = {}
        for r in rows:
            result.setdefault(r["track_name"], []).append((r["ratio"], r["midpoint"]))
        return result

    def delete_curve_point(self, track_name: str, ratio: float, midpoint: float) -> None:
        with self._connect() as con:
            con.execute(
                "DELETE FROM curve_points WHERE track_name=? AND ratio=? AND midpoint=?",
                (track_name, ratio, midpoint),
            )

    def save_curve_params(self, track_name: str, a: float, b: float) -> None:
        try:
            with self._connect() as con:
                con.execute(
                    """INSERT INTO curve_params (track_name, a, b, updated_at) VALUES (?, ?, ?, ?)
                       ON CONFLICT(track_name) DO UPDATE
                           SET a=excluded.a, b=excluded.b, updated_at=excluded.updated_at""",
                    (track_name, a, b, _now()),
                )
        except Exception as e:
            logger.error(f"Error saving curve params: {e}")

    def get_curve_params(self, track_name: str) -> Optional[Dict[str, float]]:
        with self._connect() as con:
            row = con.execute(
                "SELECT a, b FROM curve_params WHERE track_name = ?", (track_name,)
            ).fetchone()
        return {"a": row["a"], "b": row["b"]} if row else None

    def get_all_curve_params(self) -> Dict[str, Dict[str, float]]:
        with self._connect() as con:
            rows = con.execute("SELECT track_name, a, b FROM curve_params").fetchall()
        return {r["track_name"]: {"a": r["a"], "b": r["b"]} for r in rows}

    def save_curve_global(self, key: str, value: float) -> None:
        try:
            with self._connect() as con:
                con.execute(
                    "INSERT INTO curve_globals (key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (key, value),
                )
        except Exception as e:
            logger.error(f"Error saving curve global {key}: {e}")

    def get_curve_global(self, key: str, default: float = 0.0) -> float:
        with self._connect() as con:
            row = con.execute(
                "SELECT value FROM curve_globals WHERE key = ?", (key,)
            ).fetchone()
        return row["value"] if row else default
