#!/usr/bin/env python3
"""
Cleanup script for the formulas table
This will drop the old formulas table and recreate it with the new schema
Run this once to fix the database schema issues
"""

import sqlite3
from pathlib import Path

DB_PATH = "ai_data.db"


def cleanup_formulas_table():
    """Drop and recreate the formulas table with correct schema"""
    
    if not Path(DB_PATH).exists():
        print(f"Database {DB_PATH} not found")
        return False
    
    print(f"\n{'='*60}")
    print(f"CLEANUP FORMULAS TABLE")
    print(f"{'='*60}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check current table structure
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='formulas'")
    table_exists = cursor.fetchone()
    
    if table_exists:
        print(f"\nCurrent formulas table columns:")
        cursor.execute("PRAGMA table_info(formulas)")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  {col[1]} ({col[2]}) - Nullable: {not col[3]}")
        
        # Backup existing data
        cursor.execute("SELECT COUNT(*) FROM formulas")
        count = cursor.fetchone()[0]
        print(f"\nFound {count} existing formulas")
        
        if count > 0:
            print(f"\nBacking up existing formulas to formulas_backup table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS formulas_backup AS 
                SELECT * FROM formulas
            """)
            print(f"  Backup created")
        
        # Drop the old table
        print(f"\nDropping old formulas table...")
        cursor.execute("DROP TABLE formulas")
        print(f"  Table dropped")
    else:
        print(f"\nNo existing formulas table found")
    
    # Create new table with correct schema
    print(f"\nCreating new formulas table with correct schema...")
    cursor.execute("""
        CREATE TABLE formulas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track TEXT NOT NULL,
            vehicle_class TEXT NOT NULL,
            a REAL NOT NULL,
            b REAL NOT NULL,
            session_type TEXT NOT NULL,
            confidence REAL DEFAULT 1.0,
            data_points_used INTEGER DEFAULT 0,
            avg_error REAL DEFAULT 0.0,
            max_error REAL DEFAULT 0.0,
            vehicles_in_class TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_used TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(track, vehicle_class, session_type)
        )
    """)
    print(f"  New table created")
    
    # Restore data from backup if possible, converting vehicle to vehicle_class
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='formulas_backup'")
    backup_exists = cursor.fetchone()
    
    if backup_exists:
        print(f"\nRestoring data from backup (converting vehicle to vehicle_class)...")
        cursor.execute("""
            INSERT INTO formulas (track, vehicle_class, a, b, session_type, confidence, data_points_used, avg_error, max_error, created_at, last_used)
            SELECT track, vehicle, a, b, session_type, confidence, data_points_used, avg_error, max_error, created_at, last_used
            FROM formulas_backup
            WHERE vehicle IS NOT NULL
        """)
        restored = cursor.rowcount
        print(f"  Restored {restored} formulas")
        
        # Drop backup table
        cursor.execute("DROP TABLE formulas_backup")
        print(f"  Backup table dropped")
    
    conn.commit()
    conn.close()
    
    # Verify new table
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM formulas")
    count = cursor.fetchone()[0]
    print(f"\n✓ New formulas table has {count} entries")
    
    print(f"\nNew table structure:")
    cursor.execute("PRAGMA table_info(formulas)")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  {col[1]} ({col[2]})")
    
    conn.close()
    
    print(f"\n{'='*60}")
    print(f"CLEANUP COMPLETE")
    print(f"{'='*60}\n")
    
    return True


def cleanup_data_points():
    """Optional: Clean up data points for Testtrack"""
    print(f"\n{'='*60}")
    print(f"CLEANUP DATA POINTS FOR TESTTRACK")
    print(f"{'='*60}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check data points for Testtrack
    cursor.execute("SELECT COUNT(*) FROM data_points WHERE track LIKE '%Test%'")
    count = cursor.fetchone()[0]
    print(f"Found {count} data points for tracks containing 'Test'")
    
    if count > 0:
        response = input(f"\nDelete these {count} test data points? (y/n): ").lower().strip()
        if response == 'y':
            cursor.execute("DELETE FROM data_points WHERE track LIKE '%Test%'")
            deleted = cursor.rowcount
            conn.commit()
            print(f"  Deleted {deleted} test data points")
        else:
            print(f"  Keeping test data points")
    
    conn.close()
    print(f"{'='*60}\n")


if __name__ == "__main__":
    print("\n⚠️  WARNING: This script will drop and recreate the formulas table!")
    print("   Existing formulas will be backed up and restored where possible.")
    print("   Data points will NOT be affected.\n")
    
    response = input("Continue? (y/n): ").lower().strip()
    
    if response == 'y':
        cleanup_formulas_table()
        
        # Optional: Clean up test data points
        response2 = input("\nAlso clean up test data points (tracks containing 'Test')? (y/n): ").lower().strip()
        if response2 == 'y':
            cleanup_data_points()
        
        print("\n✓ Cleanup complete. You can now restart the application.")
    else:
        print("\nCleanup cancelled.")
