#!/usr/bin/env python3
"""
Database migration script:
1. Rename data_points.vehicle to data_points.vehicle_class
2. Update vehicle class names in formulas.vehicle_class and data_points.vehicle_class
   to match standardized names from vehicle_classes.json
"""

import sqlite3
import json
import sys
import shutil
from pathlib import Path
from typing import Dict, Set, Tuple, Optional

# Paths
DB_PATH = "ai_data.db"
VEHICLE_CLASSES_FILE = Path(__file__).parent / "vehicle_classes.json"


def load_vehicle_mapping() -> Tuple[Dict[str, str], Dict[str, Set[str]]]:
    """Load vehicle classes and create mapping from vehicle name to class."""
    if not VEHICLE_CLASSES_FILE.exists():
        print(f"Error: {VEHICLE_CLASSES_FILE} not found!")
        return {}, {}
    
    try:
        with open(VEHICLE_CLASSES_FILE, 'r') as f:
            classes_data = json.load(f)
    except Exception as e:
        print(f"Error loading {VEHICLE_CLASSES_FILE}: {e}")
        return {}, {}
    
    vehicle_to_class = {}
    class_to_vehicles = {}
    
    for class_name, class_info in classes_data.items():
        vehicles = class_info.get("vehicles", [])
        class_to_vehicles[class_name] = set(vehicles)
        
        for vehicle in vehicles:
            vehicle_lower = vehicle.lower()
            vehicle_to_class[vehicle_lower] = class_name
            vehicle_to_class[vehicle] = class_name
    
    print(f"Loaded {len(vehicle_to_class)} vehicle mappings into {len(class_to_vehicles)} classes")
    return vehicle_to_class, class_to_vehicles


def get_standardized_class(class_name: str, vehicle_to_class: Dict[str, str]) -> Optional[str]:
    """Get standardized class name for a given class or vehicle name."""
    if not class_name:
        return None
    
    # Try direct lookup
    if class_name in vehicle_to_class:
        return vehicle_to_class[class_name]
    
    # Try case-insensitive
    class_lower = class_name.lower()
    if class_lower in vehicle_to_class:
        return vehicle_to_class[class_lower]
    
    # Try partial match
    for vehicle_key, mapped_class in vehicle_to_class.items():
        if class_lower == vehicle_key.lower():
            return mapped_class
        if vehicle_key.lower() in class_lower or class_lower in vehicle_key.lower():
            return mapped_class
    
    return None


def rename_data_points_column(conn: sqlite3.Connection, dry_run: bool = True) -> bool:
    """Rename data_points.vehicle to data_points.vehicle_class"""
    cursor = conn.cursor()
    
    # Check if column exists and needs renaming
    cursor.execute("PRAGMA table_info(data_points)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'vehicle_class' in columns:
        print("  Column 'vehicle_class' already exists in data_points")
        return True
    
    if 'vehicle' not in columns:
        print("  Error: Column 'vehicle' not found in data_points")
        return False
    
    if dry_run:
        print("  Would rename column 'vehicle' -> 'vehicle_class' in data_points table")
        return True
    
    # Rename the column
    print("  Renaming column 'vehicle' -> 'vehicle_class'...")
    
    # SQLite doesn't support direct column rename, need to recreate table
    # Get current table schema
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='data_points'")
    old_schema = cursor.fetchone()[0]
    
    # Create new table with renamed column
    cursor.execute("""
        CREATE TABLE data_points_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track TEXT NOT NULL,
            vehicle_class TEXT NOT NULL,
            ratio REAL NOT NULL,
            lap_time REAL NOT NULL,
            session_type TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Copy data
    cursor.execute("""
        INSERT INTO data_points_new (id, track, vehicle_class, ratio, lap_time, session_type, created_at)
        SELECT id, track, vehicle, ratio, lap_time, session_type, created_at FROM data_points
    """)
    
    # Drop old table and rename new one
    cursor.execute("DROP TABLE data_points")
    cursor.execute("ALTER TABLE data_points_new RENAME TO data_points")
    
    # Recreate indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_track ON data_points(track)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_vehicle_class ON data_points(vehicle_class)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_session ON data_points(session_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_track_session ON data_points(track, session_type)")
    
    print("  ✓ Column renamed successfully")
    return True


def update_formulas_table(conn: sqlite3.Connection, vehicle_to_class: Dict[str, str], dry_run: bool = True) -> int:
    """Update vehicle_class values in formulas table to standardized names."""
    cursor = conn.cursor()
    
    # Get all distinct vehicle_class values
    cursor.execute("SELECT DISTINCT vehicle_class FROM formulas WHERE vehicle_class IS NOT NULL AND vehicle_class != ''")
    current_classes = [row[0] for row in cursor.fetchall()]
    
    update_map = {}
    for old_class in current_classes:
        new_class = get_standardized_class(old_class, vehicle_to_class)
        if new_class and new_class != old_class:
            update_map[old_class] = new_class
            print(f"  Formula class '{old_class}' -> '{new_class}'")
        elif new_class:
            print(f"  Formula class '{old_class}' is already correct")
        else:
            print(f"  Formula class '{old_class}' - no mapping found, keeping as-is")
    
    if not update_map:
        print("  No formulas table updates needed")
        return 0
    
    if dry_run:
        # Count affected rows
        total_affected = 0
        for old_class in update_map:
            cursor.execute("SELECT COUNT(*) FROM formulas WHERE vehicle_class = ?", (old_class,))
            total_affected += cursor.fetchone()[0]
        print(f"  Would update {len(update_map)} distinct classes affecting {total_affected} formulas")
        return total_affected
    
    # Perform updates
    updated = 0
    for old_class, new_class in update_map.items():
        # Check for conflicts with existing formulas
        cursor.execute("""
            SELECT track, session_type FROM formulas 
            WHERE vehicle_class = ? AND track IN (SELECT track FROM formulas WHERE vehicle_class = ?)
        """, (new_class, old_class))
        
        conflicts = cursor.fetchall()
        
        if conflicts:
            print(f"  Warning: Conflicts found when converting '{old_class}' to '{new_class}'")
            print(f"    {len(conflicts)} formulas would conflict. Merging by deleting duplicates...")
            
            # Delete old class formulas that conflict
            for track, session_type in conflicts:
                cursor.execute("""
                    DELETE FROM formulas 
                    WHERE vehicle_class = ? AND track = ? AND session_type = ?
                """, (old_class, track, session_type))
        
        # Update remaining formulas
        cursor.execute("UPDATE formulas SET vehicle_class = ? WHERE vehicle_class = ?", (new_class, old_class))
        updated += cursor.rowcount
    
    print(f"  Updated {updated} formulas")
    return updated


def update_data_points_table(conn: sqlite3.Connection, vehicle_to_class: Dict[str, str], dry_run: bool = True) -> int:
    """Update vehicle_class values in data_points table to standardized names."""
    cursor = conn.cursor()
    
    # Get all distinct vehicle_class values
    cursor.execute("SELECT DISTINCT vehicle_class FROM data_points WHERE vehicle_class IS NOT NULL AND vehicle_class != ''")
    current_classes = [row[0] for row in cursor.fetchall()]
    
    update_map = {}
    for old_class in current_classes:
        new_class = get_standardized_class(old_class, vehicle_to_class)
        if new_class and new_class != old_class:
            update_map[old_class] = new_class
            print(f"  Data point class '{old_class}' -> '{new_class}'")
        elif new_class:
            print(f"  Data point class '{old_class}' is already correct")
        else:
            print(f"  Data point class '{old_class}' - no mapping found, keeping as-is")
    
    if not update_map:
        print("  No data_points table updates needed")
        return 0
    
    if dry_run:
        total_affected = 0
        for old_class in update_map:
            cursor.execute("SELECT COUNT(*) FROM data_points WHERE vehicle_class = ?", (old_class,))
            total_affected += cursor.fetchone()[0]
        print(f"  Would update {len(update_map)} distinct classes affecting {total_affected} data points")
        return total_affected
    
    # Perform updates
    updated = 0
    for old_class, new_class in update_map.items():
        cursor.execute("UPDATE data_points SET vehicle_class = ? WHERE vehicle_class = ?", (new_class, old_class))
        updated += cursor.rowcount
    
    print(f"  Updated {updated} data points")
    return updated


def show_summary(conn: sqlite3.Connection):
    """Show summary after migration."""
    cursor = conn.cursor()
    
    print("\n" + "=" * 60)
    print("MIGRATION SUMMARY")
    print("=" * 60)
    
    # Formulas table
    cursor.execute("SELECT DISTINCT vehicle_class, COUNT(*) FROM formulas GROUP BY vehicle_class ORDER BY vehicle_class")
    formulas_classes = cursor.fetchall()
    print(f"\nFormulas table ({len(formulas_classes)} distinct classes):")
    for class_name, count in formulas_classes[:10]:
        print(f"  {class_name}: {count} formulas")
    
    # Data points table - check column name
    cursor.execute("PRAGMA table_info(data_points)")
    columns = [col[1] for col in cursor.fetchall()]
    vehicle_column = 'vehicle_class' if 'vehicle_class' in columns else 'vehicle'
    
    cursor.execute(f"SELECT DISTINCT {vehicle_column}, COUNT(*) FROM data_points GROUP BY {vehicle_column} ORDER BY {vehicle_column}")
    data_points_classes = cursor.fetchall()
    print(f"\nData points table ({len(data_points_classes)} distinct {vehicle_column}s):")
    for class_name, count in data_points_classes[:10]:
        print(f"  {class_name}: {count} points")
    
    print("=" * 60)


def main():
    print("\n" + "=" * 60)
    print("DATABASE MIGRATION: Rename vehicle column & Standardize Classes")
    print("=" * 60)
    
    # Check if database exists
    if not Path(DB_PATH).exists():
        print(f"Error: Database '{DB_PATH}' not found!")
        return False
    
    # Load vehicle mappings
    vehicle_to_class, _ = load_vehicle_mapping()
    if not vehicle_to_class:
        print("Warning: No vehicle mappings loaded, but continuing with column rename")
    
    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Show current state
    print("\n" + "-" * 60)
    print("CURRENT DATABASE STATE")
    print("-" * 60)
    
    cursor.execute("PRAGMA table_info(data_points)")
    columns = [col[1] for col in cursor.fetchall()]
    print(f"\ndata_points table columns: {', '.join(columns)}")
    
    cursor.execute("SELECT DISTINCT vehicle_class FROM formulas LIMIT 10")
    formula_classes = [row[0] for row in cursor.fetchall()]
    print(f"\nFormulas classes (sample): {', '.join(formula_classes[:10])}")
    
    # Confirm migration
    print("\n" + "-" * 60)
    print("This migration will:")
    print("  1. Rename data_points.vehicle to data_points.vehicle_class")
    print("  2. Update formulas.vehicle_class to standardized class names")
    print("  3. Update data_points.vehicle_class to standardized class names")
    print("\nIt will NOT modify:")
    print("  - ai_results.vehicle (kept as original vehicle names)")
    print("  - race_sessions.user_vehicle (kept as original vehicle names)")
    print("-" * 60)
    
    # Dry run first
    print("\n" + "-" * 60)
    print("DRY RUN - Preview changes")
    print("-" * 60)
    
    rename_data_points_column(conn, dry_run=True)
    update_formulas_table(conn, vehicle_to_class, dry_run=True)
    update_data_points_table(conn, vehicle_to_class, dry_run=True)
    
    # Ask for confirmation
    print("\n" + "-" * 60)
    response = input("Apply these changes? (yes/no): ").lower().strip()
    
    if response != 'yes':
        print("Operation cancelled.")
        conn.close()
        return False
    
    # Create backup
    backup_path = f"{DB_PATH}.migration_backup"
    print(f"\nCreating backup at: {backup_path}")
    shutil.copy2(DB_PATH, backup_path)
    print("Backup created")
    
    # Apply changes
    print("\n" + "-" * 60)
    print("APPLYING CHANGES")
    print("-" * 60)
    
    # Start transaction
    cursor.execute("BEGIN TRANSACTION")
    
    try:
        rename_data_points_column(conn, dry_run=False)
        formulas_updated = update_formulas_table(conn, vehicle_to_class, dry_run=False)
        data_points_updated = update_data_points_table(conn, vehicle_to_class, dry_run=False)
        
        conn.commit()
        
        # Show summary
        show_summary(conn)
        
        print(f"\n✓ Migration complete!")
        print(f"  - Renamed data_points.vehicle -> vehicle_class")
        print(f"  - Updated {formulas_updated} formulas")
        print(f"  - Updated {data_points_updated} data points")
        print(f"✓ Backup saved to: {backup_path}")
        
    except Exception as e:
        conn.rollback()
        print(f"\n✗ Error during migration: {e}")
        print("Changes rolled back")
        return False
    finally:
        conn.close()
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
