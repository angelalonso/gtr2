#!/usr/bin/env python3
"""
Data Importer - Migrate existing data to simple SQLite structure
Run this once to import all your existing data points
"""

import sqlite3
from pathlib import Path
from typing import Optional, Set, Tuple

# Database paths
OLD_MAIN_DB = "live_ai_tuner.db"
OLD_TRACK_DB = "track_formulas.db"
NEW_DB = "curve_data.db"


def init_new_database():
    """Initialize the new simple database schema"""
    conn = sqlite3.connect(NEW_DB)
    cursor = conn.cursor()
    
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
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_track ON data_points(track)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_vehicle ON data_points(vehicle)")
    
    conn.commit()
    conn.close()
    print(f"✓ Created new database: {NEW_DB}")


def import_from_main_db():
    """Import data points from live_ai_tuner.db (curve_points table)"""
    if not Path(OLD_MAIN_DB).exists():
        print(f"⚠ Main database not found: {OLD_MAIN_DB}")
        return 0
    
    conn = sqlite3.connect(OLD_MAIN_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get all curve points
    cursor.execute("SELECT track_name, ratio, midpoint FROM curve_points")
    rows = cursor.fetchall()
    
    conn.close()
    
    if not rows:
        print(f"  No curve points found in {OLD_MAIN_DB}")
        return 0
    
    # Insert into new database
    new_conn = sqlite3.connect(NEW_DB)
    new_cursor = new_conn.cursor()
    
    imported = 0
    for row in rows:
        track = row["track_name"]
        ratio = row["ratio"]
        lap_time = row["midpoint"]
        
        # Check if this point already exists (avoid duplicates)
        new_cursor.execute("""
            SELECT id FROM data_points 
            WHERE track = ? AND ratio = ? AND lap_time = ? AND session_type = 'unknown'
        """, (track, ratio, lap_time))
        
        if not new_cursor.fetchone():
            new_cursor.execute("""
                INSERT INTO data_points (track, vehicle, ratio, lap_time, session_type)
                VALUES (?, ?, ?, ?, ?)
            """, (track, "Unknown", ratio, lap_time, "unknown"))
            imported += 1
    
    new_conn.commit()
    new_conn.close()
    
    print(f"  ✓ Imported {imported} points from {OLD_MAIN_DB} (as 'unknown' type)")
    return imported


def import_from_track_db():
    """Import data points from track_formulas.db (track_data_points table)"""
    if not Path(OLD_TRACK_DB).exists():
        print(f"⚠ Track database not found: {OLD_TRACK_DB}")
        return 0
    
    conn = sqlite3.connect(OLD_TRACK_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get all track data points
    cursor.execute("""
        SELECT track_name, car_class, ratio, midpoint, ratio_type 
        FROM track_data_points
    """)
    rows = cursor.fetchall()
    
    conn.close()
    
    if not rows:
        print(f"  No data points found in {OLD_TRACK_DB}")
        return 0
    
    # Insert into new database
    new_conn = sqlite3.connect(NEW_DB)
    new_cursor = new_conn.cursor()
    
    imported = 0
    for row in rows:
        track = row["track_name"]
        vehicle = row["car_class"] if row["car_class"] else "Unknown"
        ratio = row["ratio"]
        lap_time = row["midpoint"]
        session_type = row["ratio_type"] if row["ratio_type"] else "unknown"
        
        # Map ratio_type to standard values
        if session_type == 'qual':
            session_type = 'qual'
        elif session_type == 'race':
            session_type = 'race'
        else:
            session_type = 'unknown'
        
        # Check if this point already exists (avoid duplicates)
        new_cursor.execute("""
            SELECT id FROM data_points 
            WHERE track = ? AND vehicle = ? AND ratio = ? AND lap_time = ? AND session_type = ?
        """, (track, vehicle, ratio, lap_time, session_type))
        
        if not new_cursor.fetchone():
            new_cursor.execute("""
                INSERT INTO data_points (track, vehicle, ratio, lap_time, session_type)
                VALUES (?, ?, ?, ?, ?)
            """, (track, vehicle, ratio, lap_time, session_type))
            imported += 1
    
    new_conn.commit()
    new_conn.close()
    
    print(f"  ✓ Imported {imported} points from {OLD_TRACK_DB}")
    return imported


def import_from_historic_csv():
    """Import data points from historic.csv if it exists"""
    csv_path = Path("./historic.csv")
    if not csv_path.exists():
        print(f"⚠ No historic.csv found")
        return 0
    
    import csv
    
    new_conn = sqlite3.connect(NEW_DB)
    new_cursor = new_conn.cursor()
    
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
                        
                        # Check for duplicate
                        new_cursor.execute("""
                            SELECT id FROM data_points 
                            WHERE track = ? AND vehicle = ? AND ratio = ? 
                            AND lap_time = ? AND session_type = 'qual'
                        """, (track, vehicle, qual_ratio, midpoint))
                        
                        if not new_cursor.fetchone():
                            new_cursor.execute("""
                                INSERT INTO data_points (track, vehicle, ratio, lap_time, session_type)
                                VALUES (?, ?, ?, ?, 'qual')
                            """, (track, vehicle, qual_ratio, midpoint))
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
                        
                        # Check for duplicate
                        new_cursor.execute("""
                            SELECT id FROM data_points 
                            WHERE track = ? AND vehicle = ? AND ratio = ? 
                            AND lap_time = ? AND session_type = 'race'
                        """, (track, vehicle, race_ratio, midpoint))
                        
                        if not new_cursor.fetchone():
                            new_cursor.execute("""
                                INSERT INTO data_points (track, vehicle, ratio, lap_time, session_type)
                                VALUES (?, ?, ?, ?, 'race')
                            """, (track, vehicle, race_ratio, midpoint))
                            imported += 1
                except (ValueError, KeyError):
                    pass
                    
    except Exception as e:
        print(f"  Error reading historic.csv: {e}")
    
    new_conn.commit()
    new_conn.close()
    
    print(f"  ✓ Imported {imported} points from historic.csv")
    return imported


def show_summary():
    """Show summary of imported data"""
    conn = sqlite3.connect(NEW_DB)
    cursor = conn.cursor()
    
    # Total points
    cursor.execute("SELECT COUNT(*) FROM data_points")
    total = cursor.fetchone()[0]
    
    # By session type
    cursor.execute("SELECT session_type, COUNT(*) FROM data_points GROUP BY session_type")
    by_type = cursor.fetchall()
    
    # Unique tracks
    cursor.execute("SELECT COUNT(DISTINCT track) FROM data_points")
    tracks = cursor.fetchone()[0]
    
    # Unique vehicles
    cursor.execute("SELECT COUNT(DISTINCT vehicle) FROM data_points")
    vehicles = cursor.fetchone()[0]
    
    conn.close()
    
    print("\n" + "=" * 50)
    print("IMPORT SUMMARY")
    print("=" * 50)
    print(f"Total data points: {total}")
    print(f"Unique tracks: {tracks}")
    print(f"Unique vehicles: {vehicles}")
    print("\nBy session type:")
    for session_type, count in by_type:
        print(f"  {session_type}: {count}")
    print("=" * 50)


def verify_import():
    """Verify import by showing sample data"""
    conn = sqlite3.connect(NEW_DB)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT track, vehicle, ratio, lap_time, session_type, created_at 
        FROM data_points 
        LIMIT 10
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    if rows:
        print("\nSample data points:")
        print("-" * 80)
        print(f"{'Track':<20} {'Vehicle':<15} {'Ratio':<10} {'Lap Time':<10} {'Type':<8} {'Date'}")
        print("-" * 80)
        for row in rows:
            track, vehicle, ratio, lap_time, session_type, created_at = row
            date = created_at[:10] if created_at else "N/A"
            print(f"{track:<20} {vehicle:<15} {ratio:<10.4f} {lap_time:<10.2f} {session_type:<8} {date}")
        print("-" * 80)


def main():
    print("\n" + "=" * 60)
    print("DATA IMPORTER - Migrate to Simple SQLite Structure")
    print("=" * 60)
    
    # Initialize new database
    init_new_database()
    
    # Import from all sources
    total = 0
    
    print("\nImporting from live_ai_tuner.db...")
    total += import_from_main_db()
    
    print("\nImporting from track_formulas.db...")
    total += import_from_track_db()
    
    print("\nImporting from historic.csv...")
    total += import_from_historic_csv()
    
    # Show results
    if total > 0:
        show_summary()
        verify_import()
        print(f"\n✓ Successfully imported {total} total data points to {NEW_DB}")
    else:
        print("\n⚠ No data was imported. Make sure your databases exist and contain data.")
    
    print("\nYou can now run the simplified curve viewer with:")
    print("  python simple_curve_viewer.py")


if __name__ == "__main__":
    main()
