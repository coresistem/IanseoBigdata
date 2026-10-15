"""
Script untuk cek distance anomaly (304050m, 581215m).
"""
import duckdb
from db_handler import ArcheryDatabase

def check_distance_anomaly():
    """Cek distance anomaly."""
    db = ArcheryDatabase()
    conn = duckdb.connect(str(db.db_path))
    
    try:
        # Cek record dengan distance anomaly
        anomalies = conn.execute("""
            SELECT distance, COUNT(*) as count
            FROM athletes 
            WHERE distance IN ('304050m', '581215m')
            GROUP BY distance
        """).fetchall()
        
        print("Distance Anomaly:")
        for dist, count in anomalies:
            print(f"  {dist:15} | Count: {count:5,}")
        
        # Cek sample records untuk detail
        print("\nSample records:")
        for dist, count in anomalies:
            samples = conn.execute(f"""
                SELECT category, event_name, year 
                FROM athletes 
                WHERE distance = '{dist}'
                LIMIT 5
            """).fetchall()
            print(f"\n{dist}:")
            for cat, event, year in samples:
                print(f"  - {cat} | {event} | {year}")
            
    finally:
        conn.close()

if __name__ == "__main__":
    check_distance_anomaly()
