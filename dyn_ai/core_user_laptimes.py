#!/usr/bin/env python3
"""
User laptimes history module for Live AI Tuner
Stores user lap times per combo (track, vehicle_class, session_type)
with automatic trimming based on nr_last_user_laptimes
"""

import sqlite3
import logging
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime
from statistics import median

logger = logging.getLogger(__name__)


class UserLapTimesManager:
    """Manages user lap times history with automatic trimming"""
    
    def __init__(self, db_path: str, max_laptimes_per_combo: int = 1):
        self.db_path = db_path
        self.max_laptimes_per_combo = max_laptimes_per_combo
        self._init_database()
    
    def set_max_laptimes(self, max_laptimes: int):
        """Update the maximum number of laptimes per combo"""
        self.max_laptimes_per_combo = max_laptimes
    
    def _init_database(self):
        """Initialize the user_laptimes table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_laptimes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                track TEXT NOT NULL,
                vehicle_class TEXT NOT NULL,
                session_type TEXT NOT NULL,
                lap_time REAL NOT NULL,
                ratio REAL NOT NULL,
                timestamp TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_laptimes_combo ON user_laptimes(track, vehicle_class, session_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_laptimes_timestamp ON user_laptimes(timestamp)")
        
        conn.commit()
        conn.close()
        logger.debug(f"Initialized user_laptimes table with max per combo: {self.max_laptimes_per_combo}")
    
    def add_laptime(self, track: str, vehicle_class: str, session_type: str, 
                    lap_time: float, ratio: float, timestamp: str = None) -> bool:
        """
        Add a new user laptime for a combo.
        Automatically trims old entries if exceeding max_laptimes_per_combo.
        
        Args:
            track: Track name
            vehicle_class: Vehicle class name
            session_type: 'qual' or 'race'
            lap_time: Lap time in seconds
            ratio: Current ratio at the time of the lap
            timestamp: Optional timestamp (ISO format), uses current time if None
        
        Returns:
            True if successful, False otherwise
        """
        if not track or not vehicle_class or not session_type:
            logger.error(f"Missing required fields: track={track}, class={vehicle_class}, session={session_type}")
            return False
        
        if lap_time <= 0:
            logger.error(f"Invalid lap time: {lap_time}")
            return False
        
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO user_laptimes (track, vehicle_class, session_type, lap_time, ratio, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (track, vehicle_class, session_type, lap_time, ratio, timestamp))
            
            conn.commit()
            logger.debug(f"Added user laptime: {track}/{vehicle_class}/{session_type} time={lap_time:.3f}s ratio={ratio:.6f}")
            
            trimmed = self._trim_combo(cursor, track, vehicle_class, session_type)
            conn.commit()
            
            if trimmed > 0:
                logger.debug(f"Trimmed {trimmed} old entries for {track}/{vehicle_class}/{session_type} (max={self.max_laptimes_per_combo})")
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding user laptime: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def _trim_combo(self, cursor, track: str, vehicle_class: str, session_type: str) -> int:
        """
        Trim old entries for a combo to max_laptimes_per_combo.
        Returns number of entries deleted.
        """
        cursor.execute("""
            SELECT COUNT(*) FROM user_laptimes
            WHERE track = ? AND vehicle_class = ? AND session_type = ?
        """, (track, vehicle_class, session_type))
        
        count = cursor.fetchone()[0]
        
        if count <= self.max_laptimes_per_combo:
            return 0
        
        to_delete = count - self.max_laptimes_per_combo
        
        cursor.execute("""
            DELETE FROM user_laptimes
            WHERE id IN (
                SELECT id FROM user_laptimes
                WHERE track = ? AND vehicle_class = ? AND session_type = ?
                ORDER BY timestamp ASC
                LIMIT ?
            )
        """, (track, vehicle_class, session_type, to_delete))
        
        return to_delete
    
    def get_laptimes_for_combo(self, track: str, vehicle_class: str, 
                                session_type: str) -> List[Tuple[float, float, str]]:
        """
        Get all laptimes for a combo.
        
        Returns:
            List of (lap_time, ratio, timestamp) tuples, sorted by timestamp ascending
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT lap_time, ratio, timestamp FROM user_laptimes
            WHERE track = ? AND vehicle_class = ? AND session_type = ?
            ORDER BY timestamp ASC
        """, (track, vehicle_class, session_type))
        
        results = cursor.fetchall()
        conn.close()
        return results
    
    def get_median_laptime_for_combo(self, track: str, vehicle_class: str, 
                                      session_type: str) -> Optional[float]:
        """
        Calculate median laptime for a combo.
        
        Returns:
            Median laptime in seconds, or None if no data
        """
        laptimes = self.get_laptimes_for_combo(track, vehicle_class, session_type)
        
        if not laptimes:
            return None
        
        times = [lt[0] for lt in laptimes]
        return median(times)
    
    def get_all_laptimes(self, track: str = None, vehicle_class: str = None,
                         session_type: str = None) -> List[Dict[str, Any]]:
        """
        Get all user laptimes, optionally filtered.
        
        Returns:
            List of dictionaries with laptime data
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT id, track, vehicle_class, session_type, lap_time, ratio, timestamp, created_at FROM user_laptimes WHERE 1=1"
        params = []
        
        if track:
            query += " AND track = ?"
            params.append(track)
        
        if vehicle_class:
            query += " AND vehicle_class = ?"
            params.append(vehicle_class)
        
        if session_type:
            query += " AND session_type = ?"
            params.append(session_type)
        
        query += " ORDER BY track, vehicle_class, session_type, timestamp DESC"
        
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return results
    
    def delete_laptime(self, laptime_id: int) -> bool:
        """Delete a specific user laptime entry by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM user_laptimes WHERE id = ?", (laptime_id,))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting user laptime: {e}")
            return False
        finally:
            conn.close()
    
    def clear_combo(self, track: str, vehicle_class: str, session_type: str) -> int:
        """Clear all laptimes for a specific combo"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                DELETE FROM user_laptimes
                WHERE track = ? AND vehicle_class = ? AND session_type = ?
            """, (track, vehicle_class, session_type))
            conn.commit()
            return cursor.rowcount
        except Exception as e:
            logger.error(f"Error clearing combo: {e}")
            return 0
        finally:
            conn.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about stored user laptimes"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM user_laptimes")
        total = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT track, vehicle_class, session_type, COUNT(*) as count
            FROM user_laptimes
            GROUP BY track, vehicle_class, session_type
            ORDER BY track, vehicle_class, session_type
        """)
        by_combo = [{"track": r[0], "vehicle_class": r[1], "session_type": r[2], "count": r[3]} 
                    for r in cursor.fetchall()]
        
        conn.close()
        
        return {
            "total_entries": total,
            "by_combo": by_combo,
            "max_per_combo": self.max_laptimes_per_combo
        }


if __name__ == "__main__":
    # Test
    import tempfile
    import os
    
    test_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    test_db.close()
    
    manager = UserLapTimesManager(test_db.name, max_laptimes_per_combo=3)
    
    # Add some test data
    manager.add_laptime("Monza", "GT Cars", "qual", 98.5, 0.95)
    manager.add_laptime("Monza", "GT Cars", "qual", 97.8, 0.96)
    manager.add_laptime("Monza", "GT Cars", "qual", 96.9, 0.97)
    manager.add_laptime("Monza", "GT Cars", "qual", 95.5, 0.98)  # Should trim to 3
    
    median_time = manager.get_median_laptime_for_combo("Monza", "GT Cars", "qual")
    print(f"Median laptime: {median_time}")
    
    stats = manager.get_stats()
    print(f"Stats: {stats}")
    
    os.unlink(test_db.name)
