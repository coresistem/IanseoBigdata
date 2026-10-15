"""
Script untuk menghapus event tertentu dari database untuk re-scraping.
"""
import duckdb
from db_handler import ArcheryDatabase

def delete_event(event_name: str):
    """Hapus event dari database."""
    db = ArcheryDatabase()
    conn = duckdb.connect(str(db.db_path))
    
    try:
        # Cek event yang akan dihapus
        events = conn.execute("""
            SELECT t.event_id, t.event_name, t.year, COUNT(a.id) as athlete_count
            FROM tournaments t
            LEFT JOIN athletes a ON t.event_id = a.event_id
            WHERE t.event_name LIKE ?
            GROUP BY t.event_id, t.event_name, t.year
        """, [f"%{event_name}%"]).fetchall()
        
        if not events:
            print(f"Event '{event_name}' tidak ditemukan.")
            return
        
        print(f"Event yang akan dihapus:")
        for event_id, name, year, count in events:
            print(f"  ID: {event_id} | {name} | {year} | Athletes: {count}")
        
        # Konfirmasi
        response = input("\nHapus event ini? (y/n): ")
        if response.lower() != 'y':
            print("Dibatalkan.")
            return
        
        # Hapus athletes dulu
        for event_id, name, year, count in events:
            deleted_athletes = conn.execute("""
                DELETE FROM athletes 
                WHERE event_id = ?
            """, [event_id])
            print(f"  Athletes dihapus: {deleted_athletes.rowcount}")
        
        # Hapus tournaments
        for event_id, name, year, count in events:
            conn.execute("""
                DELETE FROM tournaments 
                WHERE event_id = ?
            """, [event_id])
            print(f"  Tournament dihapus: {name}")
        
        print("\nEvent berhasil dihapus. Siap untuk re-scraping.")
        
    finally:
        conn.close()

if __name__ == "__main__":
    delete_event("KEJUARAAN PANAHAN ANTAR PELAJAR SE-KEPULAUAN RIAU 2024")
