#!/usr/bin/env python3
"""
Common utilities and database handler for Dyn AI Data Manager
"""

import sqlite3
import logging
from pathlib import Path
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


class SimpleCurveDatabase:
    """Simplified database handler that matches the expected interface"""
    
    def __init__(self, db_path: str = "ai_data.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
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
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_track ON data_points(track)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vehicle_class ON data_points(vehicle_class)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_session ON data_points(session_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_track_class ON data_points(track, vehicle_class)")
        
        conn.commit()
        conn.close()
    
    def data_point_exists(self, track: str, vehicle_class: str, ratio: float, lap_time: float, session_type: str) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM data_points 
                WHERE track = ? AND vehicle_class = ? AND ratio = ? AND lap_time = ? AND session_type = ?
            """, (track, vehicle_class, ratio, lap_time, session_type))
            count = cursor.fetchone()[0]
            conn.close()
            return count > 0
        except Exception as e:
            logger.error(f"Error checking existence: {e}")
            return False
    
    def add_data_point(self, track: str, vehicle_class: str, ratio: float, lap_time: float, session_type: str) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO data_points (track, vehicle_class, ratio, lap_time, session_type)
                VALUES (?, ?, ?, ?, ?)
            """, (track, vehicle_class, ratio, lap_time, session_type))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error adding data point: {e}")
            return False
    
    def get_stats(self) -> dict:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM data_points")
        total_points = cursor.fetchone()[0]
        
        cursor.execute("SELECT session_type, COUNT(*) FROM data_points GROUP BY session_type")
        by_type = dict(cursor.fetchall())
        
        cursor.execute("SELECT COUNT(DISTINCT track) FROM data_points")
        total_tracks = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT vehicle_class) FROM data_points")
        total_vehicle_classes = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_points': total_points,
            'by_type': by_type,
            'total_tracks': total_tracks,
            'total_vehicle_classes': total_vehicle_classes
        }
    
    def database_exists(self) -> bool:
        return Path(self.db_path).exists()
    
    def get_all_tracks(self) -> List[str]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT track FROM data_points ORDER BY track")
        tracks = [row[0] for row in cursor.fetchall()]
        conn.close()
        return tracks
    
    def get_all_vehicle_classes(self) -> List[str]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT vehicle_class FROM data_points ORDER BY vehicle_class")
        vehicles = [row[0] for row in cursor.fetchall()]
        conn.close()
        return vehicles
    
    def get_data_points_filtered(self, track: str = None, vehicle_class: str = None, 
                                  session_type: str = None) -> List[Tuple]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT id, track, vehicle_class, ratio, lap_time, session_type, created_at FROM data_points WHERE 1=1"
        params = []
        
        if track and track != "All":
            query += " AND track = ?"
            params.append(track)
        
        if vehicle_class and vehicle_class != "All":
            query += " AND vehicle_class = ?"
            params.append(vehicle_class)
        
        if session_type and session_type != "All":
            query += " AND session_type = ?"
            params.append(session_type)
        
        query += " ORDER BY track, vehicle_class, ratio"
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        return results
    
    def update_data_point(self, point_id: int, track: str, vehicle_class: str, 
                          ratio: float, lap_time: float, session_type: str) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE data_points 
                SET track = ?, vehicle_class = ?, ratio = ?, lap_time = ?, session_type = ?
                WHERE id = ?
            """, (track, vehicle_class, ratio, lap_time, session_type, point_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error updating data point: {e}")
            return False
    
    def delete_data_point(self, point_id: int) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM data_points WHERE id = ?", (point_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error deleting data point: {e}")
            return False
