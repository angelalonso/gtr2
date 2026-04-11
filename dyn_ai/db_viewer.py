#!/usr/bin/env python3
"""
Database Viewer for Live AI Tuner
Displays contents of both SQLite databases in formatted tables

Usage:
    python db_viewer.py                    # Show all tables from both databases
    python db_viewer.py --main-only        # Show only main database
    python db_viewer.py --track-only       # Show only track formula database
    python db_viewer.py --table race_sessions  # Show specific table
"""

import sqlite3
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional


class DatabaseViewer:
    """Display SQLite database contents in formatted tables"""
    
    def __init__(self, main_db_path: str = "live_ai_tuner.db", 
                 track_db_path: str = "track_formulas.db"):
        self.main_db_path = main_db_path
        self.track_db_path = track_db_path
        
    def _connect(self, db_path: str) -> Optional[sqlite3.Connection]:
        """Connect to database, return None if doesn't exist"""
        if not Path(db_path).exists():
            print(f"⚠️  Database not found: {db_path}")
            return None
        return sqlite3.connect(db_path)
    
    def _get_table_info(self, conn: sqlite3.Connection, table_name: str) -> List[Tuple]:
        """Get table schema information"""
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        return cursor.fetchall()
    
    def _get_table_data(self, conn: sqlite3.Connection, table_name: str, limit: int = 50) -> List[Tuple]:
        """Get table data"""
        cursor = conn.cursor()
        try:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit}")
            return cursor.fetchall()
        except sqlite3.OperationalError as e:
            print(f"Error reading {table_name}: {e}")
            return []
    
    def _get_row_count(self, conn: sqlite3.Connection, table_name: str) -> int:
        """Get number of rows in table"""
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        return cursor.fetchone()[0]
    
    def _format_time(self, time_str: str) -> str:
        """Format time string for display"""
        if not time_str:
            return "N/A"
        try:
            # Parse ISO format timestamp
            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return time_str[:19] if len(time_str) > 19 else time_str
    
    def _format_seconds(self, seconds: Optional[float]) -> str:
        """Format seconds as mm:ss.ms"""
        if seconds is None or seconds == 0:
            return "N/A"
        minutes = int(seconds) // 60
        secs = int(seconds) % 60
        ms = int((seconds - int(seconds)) * 1000)
        return f"{minutes}:{secs:02d}.{ms:03d}"
    
    def print_table(self, conn: sqlite3.Connection, table_name: str, title: str = None, 
                   max_col_width: int = 30, show_row_count: bool = True):
        """Print a formatted table"""
        if conn is None:
            return
        
        # Get table info and data
        table_info = self._get_table_info(conn, table_name)
        if not table_info:
            print(f"  ⚠️  Table '{table_name}' not found or empty")
            return
        
        data = self._get_table_data(conn, table_name)
        row_count = self._get_row_count(conn, table_name)
        
        # Print header
        if title:
            print(f"\n{'=' * 80}")
            print(f"📊 {title}")
            print(f"{'=' * 80}")
        else:
            print(f"\n{'─' * 80}")
            print(f"📋 Table: {table_name}")
        
        if show_row_count:
            print(f"   Rows: {row_count}")
        
        if not data:
            print("   (empty)")
            return
        
        # Get column names
        columns = [col[1] for col in table_info]
        
        # Prepare data rows (convert to strings, truncate if needed)
        rows = []
        for row in data:
            formatted_row = []
            for i, value in enumerate(row):
                if value is None:
                    formatted_row.append("NULL")
                elif isinstance(value, float):
                    if 'sec' in columns[i] or 'time' in columns[i].lower():
                        formatted_row.append(self._format_seconds(value))
                    else:
                        formatted_row.append(f"{value:.4f}" if value < 100 else f"{value:.2f}")
                elif isinstance(value, int):
                    formatted_row.append(str(value))
                else:
                    str_val = str(value)
                    if len(str_val) > max_col_width:
                        str_val = str_val[:max_col_width-3] + "..."
                    formatted_row.append(str_val)
            rows.append(formatted_row)
        
        # Calculate column widths
        col_widths = [len(col) for col in columns]
        for row in rows:
            for i, val in enumerate(row):
                col_widths[i] = max(col_widths[i], len(val))
        
        # Limit column widths
        col_widths = [min(w, max_col_width) for w in col_widths]
        
        # Print header row
        print("\n" + "┌" + "─" * (sum(col_widths) + len(col_widths) - 1) + "┐")
        header_cells = []
        for i, col in enumerate(columns):
            header_cells.append(col.ljust(col_widths[i]))
        print("│ " + " │ ".join(header_cells) + " │")
        
        # Print separator
        print("├" + "─┼".join(["─" * w for w in col_widths]) + "┤")
        
        # Print data rows
        for row in rows[:50]:  # Limit to 50 rows
            cells = []
            for i, val in enumerate(row):
                cells.append(val.ljust(col_widths[i]))
            print("│ " + " │ ".join(cells) + " │")
        
        if len(rows) > 50:
            print(f"│ ... and {len(rows) - 50} more rows │")
        
        print("└" + "─" * (sum(col_widths) + len(col_widths) - 1) + "┘")
    
    def show_main_database(self):
        """Display all tables from main database"""
        conn = self._connect(self.main_db_path)
        if conn is None:
            return
        
        print("\n" + "█" * 80)
        print("█  MAIN DATABASE: " + self.main_db_path)
        print("█" * 80)
        
        # List all tables
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        
        for (table_name,) in tables:
            self.print_table(conn, table_name, title=table_name)
        
        conn.close()
    
    def show_track_database(self):
        """Display all tables from track formula database"""
        conn = self._connect(self.track_db_path)
        if conn is None:
            return
        
        print("\n" + "█" * 80)
        print("█  TRACK FORMULA DATABASE: " + self.track_db_path)
        print("█" * 80)
        
        # List all tables
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        
        for (table_name,) in tables:
            self.print_table(conn, table_name, title=table_name)
        
        conn.close()
    
    def show_specific_table(self, table_name: str):
        """Display a specific table from whichever database contains it"""
        # Try main database first
        conn = self._connect(self.main_db_path)
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            if cursor.fetchone():
                self.print_table(conn, table_name, title=f"{table_name} (main database)")
                conn.close()
                return
        
        # Try track database
        conn = self._connect(self.track_db_path)
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            if cursor.fetchone():
                self.print_table(conn, table_name, title=f"{table_name} (track formula database)")
                conn.close()
                return
        
        print(f"⚠️  Table '{table_name}' not found in either database")
    
    def show_summary(self):
        """Show summary statistics from both databases"""
        print("\n" + "█" * 80)
        print("█  DATABASE SUMMARY")
        print("█" * 80)
        
        # Main database summary
        conn = self._connect(self.main_db_path)
        if conn:
            cursor = conn.cursor()
            
            # Race sessions count
            cursor.execute("SELECT COUNT(*) FROM race_sessions")
            sessions = cursor.fetchone()[0]
            
            # AI results count
            cursor.execute("SELECT COUNT(*) FROM session_ai_results")
            ai_results = cursor.fetchone()[0]
            
            # Ratio updates count
            cursor.execute("SELECT COUNT(*) FROM ratio_updates")
            ratio_updates = cursor.fetchone()[0]
            
            # Curve points count
            cursor.execute("SELECT COUNT(*) FROM curve_points")
            curve_points = cursor.fetchone()[0]
            
            # Tracks with data
            cursor.execute("SELECT COUNT(DISTINCT track_name) FROM race_sessions WHERE track_name IS NOT NULL")
            tracks = cursor.fetchone()[0]
            
            print(f"\n📁 Main Database: {self.main_db_path}")
            print(f"   ├─ Race Sessions:      {sessions}")
            print(f"   ├─ AI Results:         {ai_results}")
            print(f"   ├─ Ratio Updates:      {ratio_updates}")
            print(f"   ├─ Curve Points:       {curve_points}")
            print(f"   └─ Unique Tracks:      {tracks}")
            
            conn.close()
        
        # Track database summary
        conn = self._connect(self.track_db_path)
        if conn:
            cursor = conn.cursor()
            
            # Track formulas count
            cursor.execute("SELECT COUNT(*) FROM track_formulas")
            formulas = cursor.fetchone()[0]
            
            # Data points count
            cursor.execute("SELECT COUNT(*) FROM track_data_points")
            data_points = cursor.fetchone()[0]
            
            # Car classes count
            cursor.execute("SELECT COUNT(*) FROM car_classes")
            car_classes = cursor.fetchone()[0]
            
            # Unique tracks
            cursor.execute("SELECT COUNT(DISTINCT track_name) FROM track_data_points")
            tracks = cursor.fetchone()[0]
            
            print(f"\n📁 Track Formula Database: {self.track_db_path}")
            print(f"   ├─ Track Formulas:     {formulas}")
            print(f"   ├─ Data Points:        {data_points}")
            print(f"   ├─ Car Classes:        {car_classes}")
            print(f"   └─ Unique Tracks:      {tracks}")
            
            # Show formula summary by track
            if formulas > 0:
                print(f"\n   📊 Formula Summary by Track:")
                cursor.execute("""
                    SELECT track_name, car_class, a, b, n_points, fit_quality 
                    FROM track_formulas 
                    ORDER BY track_name, car_class
                """)
                rows = cursor.fetchall()
                for row in rows:
                    track, car, a, b, points, quality = row
                    quality_icon = "✅" if quality == "least_squares" else "⚠️" if quality == "exact_2pt" else "🔶"
                    print(f"      {quality_icon} {track} [{car}]: T = {a:.3f}/R + {b:.3f}  ({points} pts, {quality})")
            
            conn.close()
    
    def show_recent_sessions(self, limit: int = 10):
        """Show recent race sessions with AI stats"""
        conn = self._connect(self.main_db_path)
        if conn is None:
            return
        
        print("\n" + "█" * 80)
        print(f"█  RECENT RACE SESSIONS (last {limit})")
        print("█" * 80)
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT rs.id, rs.timestamp, rs.track_name, rs.qual_ratio, rs.race_ratio,
                   COUNT(ai.id) as ai_count
            FROM race_sessions rs
            LEFT JOIN session_ai_results ai ON ai.session_id = rs.id
            GROUP BY rs.id
            ORDER BY rs.timestamp DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        
        if not rows:
            print("   No sessions found")
            conn.close()
            return
        
        print("\n┌────┬─────────────────────┬──────────────────────────────┬──────────────┬──────────────┬─────────┐")
        print("│ ID │      Timestamp      │         Track Name            │  Qual Ratio  │  Race Ratio  │ AI Count│")
        print("├────┼─────────────────────┼──────────────────────────────┼──────────────┼──────────────┼─────────┤")
        
        for row in rows:
            session_id, timestamp, track, qual, race, ai_count = row
            ts_short = self._format_time(timestamp)[:19] if timestamp else "N/A"
            track_short = (track or "Unknown")[:28]
            qual_str = f"{qual:.6f}" if qual else "N/A"
            race_str = f"{race:.6f}" if race else "N/A"
            print(f"│ {session_id:2} │ {ts_short:19} │ {track_short:28} │ {qual_str:12} │ {race_str:12} │ {ai_count:7} │")
        
        print("└────┴─────────────────────┴──────────────────────────────┴──────────────┴──────────────┴─────────┘")
        
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Display contents of Live AI Tuner SQLite databases",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python db_viewer.py                    # Show all tables
    python db_viewer.py --summary          # Show only summary statistics
    python db_viewer.py --recent 20        # Show last 20 race sessions
    python db_viewer.py --main-only        # Show only main database
    python db_viewer.py --track-only       # Show only track formula database
    python db_viewer.py --table race_sessions  # Show specific table
        """
    )
    
    parser.add_argument("--main-db", default="live_ai_tuner.db",
                        help="Path to main database (default: live_ai_tuner.db)")
    parser.add_argument("--track-db", default="track_formulas.db",
                        help="Path to track formula database (default: track_formulas.db)")
    parser.add_argument("--main-only", action="store_true",
                        help="Show only main database")
    parser.add_argument("--track-only", action="store_true",
                        help="Show only track formula database")
    parser.add_argument("--table", "-t", type=str,
                        help="Show only a specific table")
    parser.add_argument("--summary", "-s", action="store_true",
                        help="Show summary statistics only")
    parser.add_argument("--recent", "-r", type=int, nargs="?", const=10,
                        help="Show recent race sessions (default: 10)")
    
    args = parser.parse_args()
    
    viewer = DatabaseViewer(args.main_db, args.track_db)
    
    if args.summary:
        viewer.show_summary()
    elif args.recent:
        viewer.show_recent_sessions(args.recent)
    elif args.table:
        viewer.show_specific_table(args.table)
    elif args.main_only:
        viewer.show_main_database()
    elif args.track_only:
        viewer.show_track_database()
    else:
        # Show everything
        viewer.show_summary()
        viewer.show_main_database()
        viewer.show_track_database()


if __name__ == "__main__":
    main()
