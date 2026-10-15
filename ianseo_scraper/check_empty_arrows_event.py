"""
Script untuk cek nama event dengan arrows kosong.
"""
import duckdb
from db_handler import ArcheryDatabase

def check_empty_arrows_event():
    """Cek nama event dengan arrows kosong."""
    db = ArcheryDatabase()
    conn = duckdb.connect(str(db.db_path))
    
    try:
        # Cek apakah records dengan arrows=0 punya event_id
        null_event = conn.execute("""
            SELECT COUNT(*) 
            FROM athletes 
            WHERE (arrows = 0 OR arrows IS NULL) AND (event_id IS NULL OR event_id = '')
        """).fetchone()[0]
        
        has_event = conn.execute("""
            SELECT COUNT(*) 
            FROM athletes 
            WHERE (arrows = 0 OR arrows IS NULL) AND event_id IS NOT NULL AND event_id != ''
        """).fetchone()[0]
        
        print(f"Records dengan arrows=0 dan event_id NULL: {null_event}")
        print(f"Records dengan arrows=0 dan event_id terisi: {has_event}")
        
        # Cek event dengan arrows kosong (hanya yang punya event_id)
        events = conn.execute("""
            SELECT t.event_name, t.year, COUNT(a.id) as count
            FROM athletes a
            INNER JOIN tournaments t ON a.event_id = t.event_id
            WHERE a.arrows = 0 OR a.arrows IS NULL
            GROUP BY t.event_name, t.year
            HAVING COUNT(a.id) > 0
            ORDER BY count DESC
        """).fetchall()
        
        print(f"\nEvent dengan arrows kosong ({len(events)} events):")
        for event, year, count in events:
            print(f"  - {event} ({year}) | Count: {count}")
        
        if len(events) == 0:
            print("Tidak ada event dengan arrows kosong yang terdeteksi.")
            print("Mungkin arrows=0 sudah tersebar di banyak event dengan count kecil per event.")
        
    finally:
        conn.close()

if __name__ == "__main__":
    check_empty_arrows_event()
