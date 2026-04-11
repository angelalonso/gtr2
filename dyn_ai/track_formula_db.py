"""
Track Formula Database - Stores formula variables per track and car set

This database stores the hyperbolic curve parameters (a and b) for each
combination of track and car class, allowing different curves for different
vehicle categories on the same track.

Schema
------
track_formulas
    Stores fitted curve parameters per track and car class.
    Primary key: (track_name, car_class)
"""

import sqlite3
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional, List, Dict, Tuple

logger = logging.getLogger(__name__)

# ── Schema ─────────────────────────────────────────────────────────────────────

_DDL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS track_formulas (
    track_name      TEXT NOT NULL,
    car_class       TEXT NOT NULL,
    a               REAL NOT NULL,           -- sensitivity parameter
    b               REAL NOT NULL,           -- floor time in seconds
    global_k        REAL,                    -- stored k value for this fit
    fit_quality     TEXT,                    -- 'exact_2pt', 'least_squares', 'bootstrap_1pt'
    n_points        INTEGER,                 -- number of data points used
    rmse            REAL,                    -- root mean square error of fit
    updated_at      TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    PRIMARY KEY (track_name, car_class)
);

CREATE INDEX IF NOT EXISTS idx_track_formulas_track ON track_formulas(track_name);
CREATE INDEX IF NOT EXISTS idx_track_formulas_car ON track_formulas(car_class);

CREATE TABLE IF NOT EXISTS track_data_points (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    track_name      TEXT NOT NULL,
    car_class       TEXT NOT NULL,
    ratio           REAL NOT NULL,
    midpoint        REAL NOT NULL,           -- (best + worst) / 2
    best_lap        REAL,
    worst_lap       REAL,
    ratio_type      TEXT,                    -- 'qual' or 'race'
    added_at        TEXT NOT NULL,
    FOREIGN KEY (track_name, car_class) REFERENCES track_formulas(track_name, car_class) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_data_points_track_car ON track_data_points(track_name, car_class);

CREATE TABLE IF NOT EXISTS car_classes (
    car_class       TEXT PRIMARY KEY,
    description     TEXT,
    created_at      TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TrackFormulaDB:
    """SQLite database for track-specific formula variables per car class."""

    def __init__(self, db_path: str = "track_formulas.db"):
        self.db_path = str(db_path)
        self._init_schema()

    def _init_schema(self):
        with self._connect() as con:
            con.executescript(_DDL)
        logger.info(f"Track formula database ready: {self.db_path}")

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

    # ── Car class management ──────────────────────────────────────────────────

    def add_car_class(self, car_class: str, description: str = "") -> bool:
        """Register a car class."""
        try:
            with self._connect() as con:
                con.execute(
                    "INSERT OR IGNORE INTO car_classes (car_class, description, created_at) VALUES (?, ?, ?)",
                    (car_class, description, _now()),
                )
            return True
        except Exception as e:
            logger.error(f"Error adding car class: {e}")
            return False

    def get_car_classes(self) -> List[str]:
        """Get all registered car classes."""
        with self._connect() as con:
            rows = con.execute("SELECT car_class FROM car_classes ORDER BY car_class").fetchall()
        return [r["car_class"] for r in rows]

    def get_car_class_description(self, car_class: str) -> Optional[str]:
        with self._connect() as con:
            row = con.execute(
                "SELECT description FROM car_classes WHERE car_class = ?", (car_class,)
            ).fetchone()
        return row["description"] if row else None

    # ── Data points ───────────────────────────────────────────────────────────

    def add_data_point(
        self,
        track_name: str,
        car_class: str,
        ratio: float,
        best_lap: float,
        worst_lap: float,
        ratio_type: str = None
    ) -> bool:
        """
        Add a data point for a track/car combination.

        Parameters
        ----------
        track_name : str
            Name of the track
        car_class : str
            Vehicle class (e.g., "Formula Senior", "GT1")
        ratio : float
            The AIW ratio used
        best_lap : float
            Best AI lap time in seconds
        worst_lap : float
            Worst AI lap time in seconds
        ratio_type : str, optional
            'qual' or 'race'
        """
        midpoint = (best_lap + worst_lap) / 2

        try:
            with self._connect() as con:
                # Ensure car class exists
                con.execute(
                    "INSERT OR IGNORE INTO car_classes (car_class, created_at) VALUES (?, ?)",
                    (car_class, _now()),
                )

                con.execute(
                    """INSERT INTO track_data_points
                       (track_name, car_class, ratio, midpoint, best_lap, worst_lap, ratio_type, added_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (track_name, car_class, ratio, midpoint, best_lap, worst_lap, ratio_type, _now()),
                )
            logger.info(f"Added data point: {track_name} [{car_class}] R={ratio:.4f} T={midpoint:.3f}s")
            return True
        except Exception as e:
            logger.error(f"Error adding data point: {e}")
            return False

    def get_data_points(
        self, track_name: str, car_class: str = None
    ) -> List[Tuple[float, float]]:
        """Get all data points for a track/car combination as (ratio, midpoint)."""
        with self._connect() as con:
            if car_class:
                rows = con.execute(
                    """SELECT ratio, midpoint FROM track_data_points
                       WHERE track_name = ? AND car_class = ?
                       ORDER BY ratio""",
                    (track_name, car_class),
                ).fetchall()
            else:
                rows = con.execute(
                    """SELECT ratio, midpoint FROM track_data_points
                       WHERE track_name = ?
                       ORDER BY ratio""",
                    (track_name,),
                ).fetchall()
        return [(r["ratio"], r["midpoint"]) for r in rows]

    def get_all_data_points(self) -> Dict[Tuple[str, str], List[Tuple[float, float]]]:
        """Get all data points grouped by (track_name, car_class)."""
        with self._connect() as con:
            rows = con.execute(
                """SELECT track_name, car_class, ratio, midpoint
                   FROM track_data_points ORDER BY track_name, car_class, ratio"""
            ).fetchall()
        result: Dict[Tuple[str, str], List[Tuple[float, float]]] = {}
        for r in rows:
            key = (r["track_name"], r["car_class"])
            result.setdefault(key, []).append((r["ratio"], r["midpoint"]))
        return result

    def delete_data_point(self, track_name: str, car_class: str, ratio: float, midpoint: float) -> bool:
        """Delete a specific data point."""
        try:
            with self._connect() as con:
                con.execute(
                    """DELETE FROM track_data_points
                       WHERE track_name = ? AND car_class = ? AND ratio = ? AND midpoint = ?""",
                    (track_name, car_class, ratio, midpoint),
                )
            return True
        except Exception as e:
            logger.error(f"Error deleting data point: {e}")
            return False

    # ── Formula storage ───────────────────────────────────────────────────────

    def save_formula(
        self,
        track_name: str,
        car_class: str,
        a: float,
        b: float,
        global_k: float = None,
        fit_quality: str = None,
        n_points: int = 0,
        rmse: float = None,
    ) -> bool:
        """Save or update formula parameters for a track/car combination."""
        try:
            with self._connect() as con:
                # Check if exists
                existing = con.execute(
                    "SELECT 1 FROM track_formulas WHERE track_name = ? AND car_class = ?",
                    (track_name, car_class),
                ).fetchone()

                if existing:
                    con.execute(
                        """UPDATE track_formulas
                           SET a = ?, b = ?, global_k = ?, fit_quality = ?,
                               n_points = ?, rmse = ?, updated_at = ?
                           WHERE track_name = ? AND car_class = ?""",
                        (a, b, global_k, fit_quality, n_points, rmse, _now(), track_name, car_class),
                    )
                else:
                    con.execute(
                        """INSERT INTO track_formulas
                           (track_name, car_class, a, b, global_k, fit_quality, n_points, rmse, updated_at, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (track_name, car_class, a, b, global_k, fit_quality, n_points, rmse, _now(), _now()),
                    )
            logger.info(f"Saved formula for {track_name} [{car_class}]: a={a:.3f}, b={b:.3f}")
            return True
        except Exception as e:
            logger.error(f"Error saving formula: {e}")
            return False

    def get_formula(
        self, track_name: str, car_class: str
    ) -> Optional[Dict[str, float]]:
        """Get formula parameters for a track/car combination."""
        with self._connect() as con:
            row = con.execute(
                """SELECT a, b, global_k, fit_quality, n_points, rmse, updated_at
                   FROM track_formulas WHERE track_name = ? AND car_class = ?""",
                (track_name, car_class),
            ).fetchone()
        if row:
            return {
                "a": row["a"],
                "b": row["b"],
                "global_k": row["global_k"],
                "fit_quality": row["fit_quality"],
                "n_points": row["n_points"],
                "rmse": row["rmse"],
                "updated_at": row["updated_at"],
            }
        return None

    def get_all_formulas(self) -> Dict[Tuple[str, str], Dict[str, float]]:
        """Get all stored formulas."""
        with self._connect() as con:
            rows = con.execute(
                "SELECT track_name, car_class, a, b, global_k, fit_quality, n_points, rmse FROM track_formulas"
            ).fetchall()
        result = {}
        for r in rows:
            key = (r["track_name"], r["car_class"])
            result[key] = {
                "a": r["a"],
                "b": r["b"],
                "global_k": r["global_k"],
                "fit_quality": r["fit_quality"],
                "n_points": r["n_points"],
                "rmse": r["rmse"],
            }
        return result

    def get_formulas_for_track(self, track_name: str) -> Dict[str, Dict[str, float]]:
        """Get all formulas for a track (different car classes)."""
        with self._connect() as con:
            rows = con.execute(
                """SELECT car_class, a, b, global_k, fit_quality, n_points, rmse
                   FROM track_formulas WHERE track_name = ?""",
                (track_name,),
            ).fetchall()
        result = {}
        for r in rows:
            result[r["car_class"]] = {
                "a": r["a"],
                "b": r["b"],
                "global_k": r["global_k"],
                "fit_quality": r["fit_quality"],
                "n_points": r["n_points"],
                "rmse": r["rmse"],
            }
        return result

    def delete_formula(self, track_name: str, car_class: str) -> bool:
        """Delete a formula for a track/car combination."""
        try:
            with self._connect() as con:
                con.execute(
                    "DELETE FROM track_formulas WHERE track_name = ? AND car_class = ?",
                    (track_name, car_class),
                )
            return True
        except Exception as e:
            logger.error(f"Error deleting formula: {e}")
            return False

    # ── Utility methods ───────────────────────────────────────────────────────

    def get_tracks_with_data(self) -> List[str]:
        """Get all tracks that have data points."""
        with self._connect() as con:
            rows = con.execute("SELECT DISTINCT track_name FROM track_data_points").fetchall()
        return [r["track_name"] for r in rows]

    def get_car_classes_for_track(self, track_name: str) -> List[str]:
        """Get all car classes that have data for a track."""
        with self._connect() as con:
            rows = con.execute(
                "SELECT DISTINCT car_class FROM track_data_points WHERE track_name = ?",
                (track_name,),
            ).fetchall()
        return [r["car_class"] for r in rows]

    def get_stats(self) -> dict:
        """Get database statistics."""
        with self._connect() as con:
            data_points = con.execute("SELECT COUNT(*) FROM track_data_points").fetchone()[0]
            formulas = con.execute("SELECT COUNT(*) FROM track_formulas").fetchone()[0]
            tracks = con.execute("SELECT COUNT(DISTINCT track_name) FROM track_data_points").fetchone()[0]
            car_classes = con.execute("SELECT COUNT(*) FROM car_classes").fetchone()[0]
        return {
            "data_points": data_points,
            "formulas": formulas,
            "tracks": tracks,
            "car_classes": car_classes,
        }
