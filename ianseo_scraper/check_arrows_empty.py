"""
Script untuk cek kolom arrows yang kosong.
"""
import duckdb
from db_handler import ArcheryDatabase

def check_arrows_empty():
    """Cek kolom arrows yang kosong."""
    db = ArcheryDatabase()
    conn = duckdb.connect(str(db.db_path))
    
    try:
        total = conn.execute("SELECT COUNT(*) FROM athletes").fetchone()[0]
        arrows_empty = conn.execute("SELECT COUNT(*) FROM athletes WHERE arrows IS NULL").fetchone()[0]
        arrows_zero = conn.execute("SELECT COUNT(*) FROM athletes WHERE arrows = 0").fetchone()[0]
        
        print(f"Total records: {total}")
        print(f"Arrows NULL: {arrows_empty}")
        print(f"Arrows = 0: {arrows_zero}")
        print(f"Arrows kosong/0: {arrows_empty + arrows_zero}")
        
        # Cek sample category dengan arrows kosong
        if arrows_empty > 0 or arrows_zero > 0:
            print("\nSample category dengan arrows kosong/0:")
            samples = conn.execute("""
                SELECT DISTINCT category, arrows
                FROM athletes 
                WHERE arrows IS NULL OR arrows = 0
                LIMIT 20
            """).fetchall()
            for cat, arr in samples:
                print(f"  - {cat} | Arrows: {arr}")
            
    finally:
        conn.close()

if __name__ == "__main__":
    check_arrows_empty()
