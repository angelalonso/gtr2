import sqlite3
import csv
from datetime import datetime

def import_csv_to_sqlite(csv_file, db_file='racing_data.db'):
    """
    Import CSV data into SQLite database
    """
    # Connect to SQLite database (creates if doesn't exist)
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Create table with appropriate column names
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS racing_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_vehicle TEXT,
            timestamp TEXT,
            track_name TEXT,
            current_qual_ratio REAL,
            qual_ai_best REAL,
            q_ai_best_vehicle TEXT,
            qual_ai_worst REAL,
            q_ai_worst_vehicle TEXT,
            qual_user REAL,
            current_race_ratio REAL,
            race_ai_best REAL,
            r_ai_best_vehicle TEXT,
            race_ai_worst REAL,
            r_ai_worst_vehicle TEXT,
            race_user REAL
        )
    ''')
    
    # Read CSV file
    with open(csv_file, 'r', encoding='utf-8') as file:
        # Use semicolon as delimiter
        csv_reader = csv.DictReader(file, delimiter=';')
        
        # Insert each row into the database
        for row in csv_reader:
            # Convert empty strings to None (NULL in SQLite)
            for key, value in row.items():
                if value == '' or value == '0':
                    row[key] = None
            
            cursor.execute('''
                INSERT INTO racing_sessions (
                    user_vehicle, timestamp, track_name, current_qual_ratio,
                    qual_ai_best, q_ai_best_vehicle, qual_ai_worst, q_ai_worst_vehicle,
                    qual_user, current_race_ratio, race_ai_best, r_ai_best_vehicle,
                    race_ai_worst, r_ai_worst_vehicle, race_user
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row.get('User Vehicle'),
                row.get('Timestamp'),
                row.get('Track Name'),
                row.get('Current QualRatio'),
                row.get('Qual AI Best (s)'),
                row.get('Q AI Best Vehicle'),
                row.get('Qual AI Worst (s)'),
                row.get('Q AI Worst Vehicle'),
                row.get('Qual User (s)'),
                row.get('Current RaceRatio'),
                row.get('Race AI Best (s)'),
                row.get('R AI Best Vehicle'),
                row.get('Race AI Worst (s)'),
                row.get('R AI Worst Vehicle'),
                row.get('Race User (s)')
            ))
    
    # Commit changes and close connection
    conn.commit()
    
    # Get row count
    cursor.execute('SELECT COUNT(*) FROM racing_sessions')
    count = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"Successfully imported {count} records into {db_file}")
    return count

if __name__ == "__main__":
    # Import the CSV file
    csv_filename = "historic.csv"  # Change this to your CSV file path
    db_filename = "racing_data.db"
    
    try:
        num_records = import_csv_to_sqlite(csv_filename, db_filename)
        print(f"Database created: {db_filename}")
    except FileNotFoundError:
        print(f"Error: Could not find file '{csv_filename}'")
        print("Please make sure the CSV file is in the current directory")
    except Exception as e:
        print(f"An error occurred: {e}")
