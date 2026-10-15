"""
Script untuk cek hasil re-scraping event.
"""
import duckdb
from db_handler import ArcheryDatabase

def check_rescaped_event():
    """Cek hasil re-scraping event."""
    db = ArcheryDatabase()
    conn = duckdb.connect(str(db.db_path))
    
    try:
        # Cek event yang baru di-scrape
        events = conn.execute("""
            SELECT t.event_id, t.event_name, t.year, t.status, COUNT(a.id) as athlete_count
            FROM tournaments t
            LEFT JOIN athletes a ON t.event_id = a.event_id
            WHERE t.event_name LIKE '%KEJUARAAN PANAHAN ANTAR PELAJAR SE-KEPULAUAN RIAU 2024%'
            GROUP BY t.event_id, t.event_name, t.year, t.status
        """).fetchall()
        
        print("Event yang di-scrape ulang:")
        for event_id, name, year, status, count in events:
            print(f"  ID: {event_id} | {name} | {year} | Status: {status} | Athletes: {count}")
        
        if not events:
            print("Event tidak ditemukan.")
            return
        
        # Cek distance values untuk event ini
        print("\nDistance values:")
        for event_id, name, year, status, count in events:
            distances = conn.execute(f"""
                SELECT distance, COUNT(*) as count
                FROM athletes
                WHERE event_id = {event_id}
                GROUP BY distance
                ORDER BY distance
            """).fetchall()
            print(f"\n{name}:")
            for dist, cnt in distances:
                print(f"  {dist:20} | Count: {cnt}")
        
        # Cek sample records
        print("\nSample records:")
        for event_id, name, year, status, count in events:
            samples = conn.execute(f"""
                SELECT category, division, distance, gender, arrows
                FROM athletes
                WHERE event_id = {event_id}
                LIMIT 10
            """).fetchall()
            print(f"\n{name}:")
            for cat, div, dist, gen, arr in samples:
                print(f"  Category: {cat}")
                print(f"    Division: {div} | Distance: {dist} | Gender: {gen} | Arrows: {arr}")
            
    finally:
        conn.close()

if __name__ == "__main__":
    check_rescaped_event()
