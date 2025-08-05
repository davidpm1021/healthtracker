#!/usr/bin/env python3
"""
Insert data directly into SQLite database (bypassing API)
"""
import sqlite3
from datetime import datetime

# Your historical data converted
data = [
    ("2025-08-02", 107.95, 77, 19),  # 238 lbs
    ("2025-08-03", 109.32, 72, 31),  # 241 lbs  
    ("2025-08-04", 107.50, 70, 27),  # 237 lbs
    ("2025-08-05", 106.77, 68, 32),  # 235.5 lbs
]

def insert_data():
    """Insert data directly into database"""
    try:
        # Connect to database
        conn = sqlite3.connect('healthtracker.db')
        cursor = conn.cursor()
        
        print("🔄 Inserting historical data directly into database...")
        
        for day_date, weight_kg, sleeping_hr, sleeping_hrv in data:
            print(f"📅 Processing {day_date}...")
            
            # Insert raw weight data
            cursor.execute("""
                INSERT OR REPLACE INTO raw_points 
                (metric, start_time, end_time, value, unit, source, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                'weight',
                f"{day_date}T07:00:00Z",
                f"{day_date}T07:00:00Z", 
                weight_kg,
                'kg',
                'manual_historical',
                datetime.now().isoformat() + 'Z'
            ))
            
            # Insert raw heart rate data  
            cursor.execute("""
                INSERT OR REPLACE INTO raw_points 
                (metric, start_time, end_time, value, unit, source, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                'heart_rate',
                f"{day_date}T06:00:00Z",
                f"{day_date}T06:00:00Z",
                sleeping_hr,
                'bpm', 
                'manual_historical',
                datetime.now().isoformat() + 'Z'
            ))
            
            # Insert HRV as manual entry
            cursor.execute("""
                INSERT OR REPLACE INTO manual_entries 
                (date, metric, value, unit, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                day_date,
                'hrv',
                sleeping_hrv,
                'ms',
                'Sleeping HRV from historical data',
                datetime.now().isoformat() + 'Z'
            ))
            
            # Create daily summary for weight
            cursor.execute("""
                INSERT OR REPLACE INTO daily_summaries 
                (date, metric, value, unit, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                day_date,
                'weight',
                weight_kg,
                'kg',
                datetime.now().isoformat() + 'Z'
            ))
            
            # Create daily summary for heart rate  
            cursor.execute("""
                INSERT OR REPLACE INTO daily_summaries 
                (date, metric, value, unit, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                day_date,
                'heart_rate', 
                sleeping_hr,
                'bpm',
                datetime.now().isoformat() + 'Z'
            ))
            
            print(f"  ✅ Weight: {weight_kg:.1f} kg")
            print(f"  ✅ Sleeping HR: {sleeping_hr} bpm") 
            print(f"  ✅ Sleeping HRV: {sleeping_hrv} ms")
        
        # Commit all changes
        conn.commit()
        conn.close()
        
        print("🎉 Successfully inserted all 4 days of historical data!")
        print("📊 You can now view your data in the dashboard")
        
    except Exception as e:
        print(f"❌ Error inserting data: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()

if __name__ == "__main__":
    insert_data()