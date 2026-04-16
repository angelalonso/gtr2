#!/usr/bin/env python3
"""
Database module for curve data management
Provides reusable database operations for track/vehicle curve data
"""

import sqlite3
import traceback
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from datetime import datetime


class CurveDatabase:
    """Reusable database handler for curve data points"""
    
    def __init__(self, db_path: str = "ai_data.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema if it doesn't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Data points table (existing)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS data_points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                track TEXT NOT NULL,
                vehicle TEXT NOT NULL,
                ratio REAL NOT NULL,
                lap_time REAL NOT NULL,
                session_type TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Race sessions table
        cursor.execute("""
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
        
        # AI results table - now stores ALL AI drivers, not just best/worst
        cursor.execute("""
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
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_track ON data_points(track)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vehicle ON data_points(vehicle)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_session ON data_points(session_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_track_session ON data_points(track, session_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_race_track ON race_sessions(track_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_race_timestamp ON race_sessions(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ai_race ON ai_results(race_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ai_times ON ai_results(qual_time_sec, best_lap_sec)")
        
        conn.commit()
        conn.close()
    
    def database_exists(self) -> bool:
        """Check if database file exists"""
        return Path(self.db_path).exists()
    
    def get_all_tracks(self) -> List[str]:
        """Get all unique track names"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT track FROM data_points ORDER BY track")
        tracks = [row[0] for row in cursor.fetchall()]
        conn.close()
        return tracks
    
    def get_all_vehicles(self) -> List[str]:
        """Get all unique vehicle names"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT vehicle FROM data_points ORDER BY vehicle")
        vehicles = [row[0] for row in cursor.fetchall()]
        conn.close()
        return vehicles
    
    def get_data_points(
        self, 
        tracks: List[str], 
        vehicles: List[str],
        show_qualifying: bool = True,
        show_race: bool = True,
        show_unknown: bool = True
    ) -> List[Tuple[float, float, str]]:
        """
        Get filtered data points from database
        
        Returns list of tuples (ratio, lap_time, session_type)
        """
        if not tracks or not vehicles:
            return []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build query with placeholders
        track_placeholders = ','.join(['?' for _ in tracks])
        vehicle_placeholders = ','.join(['?' for _ in vehicles])
        
        # Build session type filter
        session_filters = []
        if show_qualifying:
            session_filters.append("session_type = 'qual'")
        if show_race:
            session_filters.append("session_type = 'race'")
        if show_unknown:
            session_filters.append("session_type = 'unknown'")
        
        if not session_filters:
            conn.close()
            return []
        
        session_clause = f"({' OR '.join(session_filters)})"
        
        query = f"""
            SELECT ratio, lap_time, session_type 
            FROM data_points 
            WHERE track IN ({track_placeholders}) 
            AND vehicle IN ({vehicle_placeholders})
            AND {session_clause}
            ORDER BY ratio
        """
        
        params = tracks + vehicles
        cursor.execute(query, params)
        
        points = [(row[0], row[1], row[2]) for row in cursor.fetchall()]
        conn.close()
        
        # Debug output
        print(f"\n[Database] get_data_points called:")
        print(f"  Tracks: {tracks}")
        print(f"  Vehicles: {vehicles}")
        print(f"  Show qualifying: {show_qualifying}")
        print(f"  Show race: {show_race}")
        print(f"  Show unknown: {show_unknown}")
        print(f"  Returned {len(points)} points")
        
        # Group by type for debugging
        qual_count = sum(1 for p in points if p[2] == 'qual')
        race_count = sum(1 for p in points if p[2] == 'race')
        unknown_count = sum(1 for p in points if p[2] == 'unknown')
        print(f"  Qual points: {qual_count}, Race points: {race_count}, Unknown: {unknown_count}")
        
        return points
    
    def get_stats(self) -> Dict[str, any]:
        """Get database statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM data_points")
        total_points = cursor.fetchone()[0]
        
        cursor.execute("SELECT session_type, COUNT(*) FROM data_points GROUP BY session_type")
        by_type = dict(cursor.fetchall())
        
        cursor.execute("SELECT COUNT(DISTINCT track) FROM data_points")
        total_tracks = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT vehicle) FROM data_points")
        total_vehicles = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM race_sessions")
        total_races = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM ai_results")
        total_ai_results = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_points': total_points,
            'by_type': by_type,
            'total_tracks': total_tracks,
            'total_vehicles': total_vehicles,
            'total_races': total_races,
            'total_ai_results': total_ai_results
        }
    
    def save_race_session(self, race_data: dict) -> Optional[str]:
        """Save a complete race session with ALL AI results"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Print debug info
            print(f"  Debug: Saving race session with data:")
            print(f"    race_id: {race_data.get('race_id')}")
            print(f"    timestamp: {race_data.get('timestamp')}")
            print(f"    track_name: {race_data.get('track_name')}")
            print(f"    ai_results count: {len(race_data.get('ai_results', []))}")
            
            # Ensure timestamp exists
            timestamp = race_data.get('timestamp')
            if not timestamp:
                timestamp = datetime.now().isoformat()
                print(f"    Generated timestamp: {timestamp}")
            
            # Ensure race_id exists
            race_id = race_data.get('race_id')
            if not race_id:
                race_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                print(f"    Generated race_id: {race_id}")
            
            # Insert race session
            cursor.execute("""
                INSERT OR REPLACE INTO race_sessions (
                    race_id, timestamp, track_name, track_folder, aiw_file,
                    qual_ratio, race_ratio, user_name, user_vehicle,
                    user_best_lap, user_best_lap_sec, user_qualifying, user_qualifying_sec
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                race_id,
                timestamp,
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
            
            print(f"    ✓ Race session inserted")
            
            # Insert ALL AI results
            ai_count = 0
            for ai in race_data.get('ai_results', []):
                cursor.execute("""
                    INSERT INTO ai_results (
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
                ai_count += 1
            
            print(f"    ✓ Inserted {ai_count} AI results")
            
            conn.commit()
            print(f"  ✓ Race session committed to database")
            return race_id
            
        except sqlite3.IntegrityError as e:
            print(f"  ✗ SQLite integrity error: {e}")
            print(f"  Full traceback:")
            traceback.print_exc()
            conn.rollback()
            return None
        except Exception as e:
            print(f"  ✗ Error saving race session: {e}")
            print(f"  Full traceback:")
            traceback.print_exc()
            conn.rollback()
            return None
        finally:
            conn.close()
    
    def add_data_point(
        self, 
        track: str, 
        vehicle: str, 
        ratio: float, 
        lap_time: float, 
        session_type: str
    ) -> bool:
        """Add a new data point to the database"""
        try:
            conn = sqlite3.connect(self.db_path)  # FIXED: use self.db_path, not self.db
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO data_points (track, vehicle, ratio, lap_time, session_type)
                VALUES (?, ?, ?, ?, ?)
            """, (track, vehicle, float(ratio), float(lap_time), session_type))
            conn.commit()
            conn.close()
            print(f"  [DB] Added {session_type} point: {track} R={float(ratio):.4f} T={float(lap_time):.2f}s")
            return True
        except Exception as e:
            print(f"Error adding data point: {e}")
            return False


    def add_data_points_batch(self, points: List[Tuple[str, str, float, float, str]]) -> int:
        """Add multiple data points in batch"""
        if not points:
            return 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        added = 0
        for track, vehicle, ratio, lap_time, session_type in points:
            try:
                cursor.execute("""
                    INSERT INTO data_points (track, vehicle, ratio, lap_time, session_type)
                    VALUES (?, ?, ?, ?, ?)
                """, (track, vehicle, ratio, lap_time, session_type))
                added += 1
            except Exception as e:
                print(f"Error adding point: {e}")
        
        conn.commit()
        conn.close()
        return added
    
    def get_race_sessions(self, track_name: str = None, limit: int = 50) -> List[Dict]:
        """Get race sessions, optionally filtered by track"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if track_name:
            cursor.execute("""
                SELECT * FROM race_sessions 
                WHERE track_name = ? 
                ORDER BY timestamp DESC LIMIT ?
            """, (track_name, limit))
        else:
            cursor.execute("SELECT * FROM race_sessions ORDER BY timestamp DESC LIMIT ?", (limit,))
        
        sessions = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return sessions
    
    def get_ai_results_for_race(self, race_id: str) -> List[Dict]:
        """Get ALL AI results for a specific race"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM ai_results WHERE race_id = ? ORDER BY slot", (race_id,))
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def get_all_ai_times_for_track(self, track_name: str, session_type: str = "race") -> List[Tuple[float, float]]:
        """
        Get all AI times for a specific track
        Returns list of (ratio, lap_time) pairs from all AI drivers across all sessions
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if session_type == "qual":
            query = """
                SELECT rs.qual_ratio, ar.qual_time_sec
                FROM race_sessions rs
                JOIN ai_results ar ON rs.race_id = ar.race_id
                WHERE rs.track_name = ? AND ar.qual_time_sec IS NOT NULL AND ar.qual_time_sec > 0
                ORDER BY rs.timestamp
            """
        else:  # race
            query = """
                SELECT rs.race_ratio, ar.best_lap_sec
                FROM race_sessions rs
                JOIN ai_results ar ON rs.race_id = ar.race_id
                WHERE rs.track_name = ? AND ar.best_lap_sec IS NOT NULL AND ar.best_lap_sec > 0
                ORDER BY rs.timestamp
            """
        
        cursor.execute(query, (track_name,))
        results = [(row[0], row[1]) for row in cursor.fetchall() if row[0] is not None and row[1] > 0]
        conn.close()
        return results


class DataImporter:
    """Handles importing data from legacy databases and CSV files"""
    
    def __init__(self, target_db: CurveDatabase):
        self.target_db = target_db
    
    def import_from_main_db(self, old_db_path: str = "live_ai_tuner.db") -> int:
        """Import data points from live_ai_tuner.db (curve_points table)"""
        if not Path(old_db_path).exists():
            return 0
        
        conn = sqlite3.connect(old_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT track_name, ratio, midpoint FROM curve_points")
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return 0
        
        imported = 0
        for row in rows:
            track = row["track_name"]
            ratio = row["ratio"]
            lap_time = row["midpoint"]
            
            existing = self.target_db.get_data_points([track], ["Unknown"], True, True, True)
            exists = any(abs(r - ratio) < 0.001 and abs(t - lap_time) < 0.01 for r, t, _ in existing)
            
            if not exists:
                if self.target_db.add_data_point(track, "Unknown", ratio, lap_time, "unknown"):
                    imported += 1
        
        return imported
    
    def import_from_track_db(self, old_db_path: str = "track_formulas.db") -> int:
        """Import data points from track_formulas.db (track_data_points table)"""
        if not Path(old_db_path).exists():
            return 0
        
        conn = sqlite3.connect(old_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT track_name, car_class, ratio, midpoint, ratio_type 
            FROM track_data_points
        """)
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return 0
        
        imported = 0
        for row in rows:
            track = row["track_name"]
            vehicle = row["car_class"] if row["car_class"] else "Unknown"
            ratio = row["ratio"]
            lap_time = row["midpoint"]
            session_type = row["ratio_type"] if row["ratio_type"] else "unknown"
            
            if session_type == 'qual':
                session_type = 'qual'
            elif session_type == 'race':
                session_type = 'race'
            else:
                session_type = 'unknown'
            
            existing = self.target_db.get_data_points([track], [vehicle], True, True, True)
            exists = any(abs(r - ratio) < 0.001 and abs(t - lap_time) < 0.01 for r, t, _ in existing)
            
            if not exists:
                if self.target_db.add_data_point(track, vehicle, ratio, lap_time, session_type):
                    imported += 1
        
        return imported
    
    def import_from_csv(self, csv_path: str = "historic.csv") -> int:
        """Import data points from historic.csv"""
        if not Path(csv_path).exists():
            return 0
        
        import csv
        
        imported = 0
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter=';')
                
                for row in reader:
                    track = row.get('Track Name', '')
                    if not track:
                        continue
                    
                    vehicle = row.get('User Vehicle', 'Unknown')
                    if not vehicle or vehicle == '0':
                        vehicle = row.get('Car', 'Unknown')
                    
                    # Import qualifying data
                    try:
                        qual_ratio = float(row.get('Current QualRatio', '0'))
                        qual_best = float(row.get('Qual AI Best (s)', '0'))
                        qual_worst = float(row.get('Qual AI Worst (s)', '0'))
                        
                        if qual_ratio > 0 and qual_best > 0 and qual_worst > 0:
                            midpoint = (qual_best + qual_worst) / 2
                            
                            existing = self.target_db.get_data_points([track], [vehicle], True, True, True)
                            exists = any(abs(r - qual_ratio) < 0.001 and abs(t - midpoint) < 0.01 for r, t, _ in existing)
                            
                            if not exists:
                                if self.target_db.add_data_point(track, vehicle, qual_ratio, midpoint, "qual"):
                                    imported += 1
                    except (ValueError, KeyError):
                        pass
                    
                    # Import race data
                    try:
                        race_ratio = float(row.get('Current RaceRatio', '0'))
                        race_best = float(row.get('Race AI Best (s)', '0'))
                        race_worst = float(row.get('Race AI Worst (s)', '0'))
                        
                        if race_ratio > 0 and race_best > 0 and race_worst > 0:
                            midpoint = (race_best + race_worst) / 2
                            
                            existing = self.target_db.get_data_points([track], [vehicle], True, True, True)
                            exists = any(abs(r - race_ratio) < 0.001 and abs(t - midpoint) < 0.01 for r, t, _ in existing)
                            
                            if not exists:
                                if self.target_db.add_data_point(track, vehicle, race_ratio, midpoint, "race"):
                                    imported += 1
                    except (ValueError, KeyError):
                        pass
                        
        except Exception as e:
            print(f"Error reading CSV: {e}")
        
        return imported


def run_importer(db_path: str = "ai_data.db"):
    """Run the importer to migrate existing data"""
    print("\n" + "=" * 60)
    print("DATA IMPORTER - Migrate to Simple SQLite Structure")
    print("=" * 60)
    
    db = CurveDatabase(db_path)
    importer = DataImporter(db)
    
    total = 0
    
    print("\nImporting from live_ai_tuner.db...")
    total += importer.import_from_main_db()
    
    print("\nImporting from track_formulas.db...")
    total += importer.import_from_track_db()
    
    print("\nImporting from historic.csv...")
    total += importer.import_from_csv()
    
    if total > 0:
        stats = db.get_stats()
        print("\n" + "=" * 50)
        print("IMPORT SUMMARY")
        print("=" * 50)
        print(f"Total data points: {stats['total_points']}")
        print(f"Unique tracks: {stats['total_tracks']}")
        print(f"Unique vehicles: {stats['total_vehicles']}")
        print(f"Total races: {stats['total_races']}")
        print(f"Total AI results: {stats['total_ai_results']}")
        print("\nBy session type:")
        for session_type, count in stats['by_type'].items():
            print(f"  {session_type}: {count}")
        print("=" * 50)
        print(f"\n✓ Successfully imported {total} total data points to {db_path}")
    else:
        print("\n⚠ No data was imported.")
    
    return total


if __name__ == "__main__":
    run_importer()
