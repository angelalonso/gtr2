#!/usr/bin/env python3
"""
Database module with connection pooling and lightweight queries
"""

import sqlite3
import threading
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
from contextlib import contextmanager

_local = threading.local()


class DatabaseManager:
    """Thread-safe database manager with connection pooling"""
    
    def __init__(self, db_path: str = "ai_data.db"):
        self.db_path = db_path
        self._init_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a connection for the current thread"""
        if not hasattr(_local, 'connection') or _local.connection is None:
            _local.connection = sqlite3.connect(self.db_path, timeout=10.0)
            _local.connection.row_factory = sqlite3.Row
        return _local.connection
    
    def _close_connection(self):
        """Close connection for current thread"""
        if hasattr(_local, 'connection') and _local.connection:
            _local.connection.close()
            _local.connection = None
    
    @contextmanager
    def cursor(self):
        """Get a cursor with automatic commit/rollback"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
    
    def _init_database(self):
        """Initialize database schema if it doesn't exist"""
        with self.cursor() as c:
            # Data points table
            c.execute("""
                CREATE TABLE IF NOT EXISTS data_points (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    track TEXT NOT NULL,
                    vehicle_class TEXT NOT NULL,
                    ratio REAL NOT NULL,
                    lap_time REAL NOT NULL,
                    session_type TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Race sessions table
            c.execute("""
                CREATE TABLE IF NOT EXISTS race_sessions (
                    race_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    track_name TEXT,
                    track_folder TEXT,
                    aiw_file TEXT,
                    qual_ratio REAL,
                    race_ratio REAL,
                    user_name TEXT,
                    user_vehicle TEXT,
                    user_best_lap TEXT,
                    user_best_lap_sec REAL,
                    user_qualifying TEXT,
                    user_qualifying_sec REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # AI results table
            c.execute("""
                CREATE TABLE IF NOT EXISTS ai_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    race_id TEXT NOT NULL,
                    slot INTEGER NOT NULL,
                    driver_name TEXT,
                    vehicle TEXT,
                    team TEXT,
                    qual_time TEXT,
                    qual_time_sec REAL,
                    best_lap TEXT,
                    best_lap_sec REAL,
                    race_time TEXT,
                    race_time_sec REAL,
                    laps INTEGER,
                    FOREIGN KEY (race_id) REFERENCES race_sessions(race_id) ON DELETE CASCADE
                )
            """)
            
            # Formulas table
            c.execute("""
                CREATE TABLE IF NOT EXISTS formulas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    track TEXT NOT NULL,
                    vehicle_class TEXT NOT NULL,
                    a REAL NOT NULL,
                    b REAL NOT NULL,
                    session_type TEXT NOT NULL,
                    data_points_used INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_used TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(track, vehicle_class, session_type)
                )
            """)
            
            # Create indexes for performance
            c.execute("CREATE INDEX IF NOT EXISTS idx_data_track_class ON data_points(track, vehicle_class)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_data_session ON data_points(session_type)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_data_track ON data_points(track)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_formulas_track_class ON formulas(track, vehicle_class)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_race_track ON race_sessions(track_name)")
    
    def database_exists(self) -> bool:
        """Check if database file exists and has tables"""
        if not Path(self.db_path).exists():
            return False
        try:
            with self.cursor() as c:
                c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='data_points'")
                return c.fetchone() is not None
        except Exception:
            return False
    
    def get_all_tracks(self) -> List[str]:
        """Get all unique track names"""
        with self.cursor() as c:
            c.execute("SELECT DISTINCT track FROM data_points ORDER BY track")
            return [row[0] for row in c.fetchall()]
    
    def get_all_vehicle_classes(self) -> List[str]:
        """Get all unique vehicle class names"""
        with self.cursor() as c:
            c.execute("SELECT DISTINCT vehicle_class FROM data_points ORDER BY vehicle_class")
            return [row[0] for row in c.fetchall()]
    
    def get_data_points(self, track: str, vehicle_classes: List[str]) -> List[Tuple[float, float, str]]:
        """Get data points for a specific track and vehicle classes"""
        if not vehicle_classes:
            return []
        
        placeholders = ','.join('?' * len(vehicle_classes))
        with self.cursor() as c:
            query = f"""
                SELECT ratio, lap_time, session_type 
                FROM data_points 
                WHERE track = ? AND vehicle_class IN ({placeholders})
                ORDER BY ratio
            """
            c.execute(query, [track] + vehicle_classes)
            return [(row[0], row[1], row[2]) for row in c.fetchall()]
    
    def get_stats(self) -> Dict[str, int]:
        """Get basic database statistics (lightweight)"""
        with self.cursor() as c:
            c.execute("SELECT COUNT(*) FROM data_points")
            total_points = c.fetchone()[0]
            
            c.execute("SELECT COUNT(DISTINCT track) FROM data_points")
            total_tracks = c.fetchone()[0]
            
            c.execute("SELECT COUNT(DISTINCT vehicle_class) FROM data_points")
            total_vehicle_classes = c.fetchone()[0]
            
            return {
                'total_points': total_points,
                'total_tracks': total_tracks,
                'total_vehicle_classes': total_vehicle_classes
            }
    
    def add_data_point(self, track: str, vehicle_class: str, ratio: float, lap_time: float, session_type: str) -> bool:
        """Add a new data point (returns True if new, False if duplicate)"""
        with self.cursor() as c:
            # Check for duplicate
            c.execute("""
                SELECT id FROM data_points 
                WHERE track = ? AND vehicle_class = ? AND ABS(ratio - ?) < 0.0001 AND ABS(lap_time - ?) < 0.01 AND session_type = ?
                LIMIT 1
            """, (track, vehicle_class, ratio, lap_time, session_type))
            if c.fetchone():
                return False
            
            c.execute("""
                INSERT INTO data_points (track, vehicle_class, ratio, lap_time, session_type)
                VALUES (?, ?, ?, ?, ?)
            """, (track, vehicle_class, ratio, lap_time, session_type))
            return True
    
    def add_data_points_batch(self, points: List[Tuple[str, str, float, float, str]]) -> int:
        """Add multiple data points in batch"""
        if not points:
            return 0
        
        added = 0
        with self.cursor() as c:
            for track, vehicle_class, ratio, lap_time, session_type in points:
                c.execute("""
                    INSERT OR IGNORE INTO data_points (track, vehicle_class, ratio, lap_time, session_type)
                    VALUES (?, ?, ?, ?, ?)
                """, (track, vehicle_class, ratio, lap_time, session_type))
                if c.rowcount > 0:
                    added += 1
        return added
    
    def save_race_session(self, race_data: dict) -> Optional[str]:
        """Save a complete race session"""
        race_id = race_data.get('race_id') or datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        
        with self.cursor() as c:
            c.execute("""
                INSERT OR REPLACE INTO race_sessions (
                    race_id, timestamp, track_name, track_folder, aiw_file,
                    qual_ratio, race_ratio, user_name, user_vehicle,
                    user_best_lap, user_best_lap_sec, user_qualifying, user_qualifying_sec
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                race_id,
                race_data.get('timestamp', datetime.now().isoformat()),
                race_data.get('track_name'),
                race_data.get('track_folder'),
                race_data.get('aiw_file'),
                race_data.get('qual_ratio'),
                race_data.get('race_ratio'),
                race_data.get('user_name'),
                race_data.get('user_vehicle'),
                race_data.get('user_best_lap'),
                race_data.get('user_best_lap_sec', 0.0),
                race_data.get('user_qualifying'),
                race_data.get('user_qualifying_sec', 0.0)
            ))
            
            for ai in race_data.get('ai_results', []):
                c.execute("""
                    INSERT OR REPLACE INTO ai_results (
                        race_id, slot, driver_name, vehicle, team,
                        qual_time, qual_time_sec, best_lap, best_lap_sec,
                        race_time, race_time_sec, laps
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    race_id,
                    ai.get('slot', 0),
                    ai.get('driver_name'),
                    ai.get('vehicle'),
                    ai.get('team'),
                    ai.get('qual_time'),
                    ai.get('qual_time_sec'),
                    ai.get('best_lap'),
                    ai.get('best_lap_sec'),
                    ai.get('race_time'),
                    ai.get('race_time_sec'),
                    ai.get('laps')
                ))
        
        return race_id
    
    def get_formula(self, track: str, vehicle_class: str, session_type: str) -> Optional[Tuple[float, float]]:
        """Get formula parameters for a track/class/session"""
        with self.cursor() as c:
            c.execute("""
                SELECT a, b FROM formulas 
                WHERE track = ? AND vehicle_class = ? AND session_type = ?
            """, (track, vehicle_class, session_type))
            row = c.fetchone()
            if row:
                return (row[0], row[1])
        return None
    
    def save_formula(self, track: str, vehicle_class: str, session_type: str, a: float, b: float, data_points: int = 1) -> bool:
        """Save or update a formula"""
        with self.cursor() as c:
            c.execute("""
                INSERT OR REPLACE INTO formulas (track, vehicle_class, a, b, session_type, data_points_used, last_used)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (track, vehicle_class, a, b, session_type, data_points))
            return True
    
    def get_ai_times_for_track(self, track: str, session_type: str = "race") -> Tuple[Optional[float], Optional[float]]:
        """Get best and worst AI times for a track"""
        with self.cursor() as c:
            if session_type == "qual":
                c.execute("""
                    SELECT MIN(qual_time_sec), MAX(qual_time_sec)
                    FROM ai_results ar
                    JOIN race_sessions rs ON ar.race_id = rs.race_id
                    WHERE rs.track_name = ? AND ar.qual_time_sec > 0
                """, (track,))
            else:
                c.execute("""
                    SELECT MIN(best_lap_sec), MAX(best_lap_sec)
                    FROM ai_results ar
                    JOIN race_sessions rs ON ar.race_id = rs.race_id
                    WHERE rs.track_name = ? AND ar.best_lap_sec > 0
                """, (track,))
            
            row = c.fetchone()
            if row and row[0] is not None:
                return (row[0], row[1] or row[0])
            return (None, None)
    
    def close(self):
        """Close database connections"""
        self._close_connection()
