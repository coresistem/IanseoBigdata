"""
Script untuk cek kolom kosong di database.
"""
import duckdb
from db_handler import ArcheryDatabase

def check_empty_columns():
    """Cek kolom kosong di tabel athletes."""
    db = ArcheryDatabase()
    conn = duckdb.connect(str(db.db_path))
    
    try:
        total = conn.execute("SELECT COUNT(*) FROM athletes").fetchone()[0]
        print(f"Total records: {total}\n")
        
        columns = ['division', 'gender', 'distance', 'arrows']
        
        for col in columns:
            if col == 'arrows':
                # Integer column - only check NULL
                empty = conn.execute(f"""
                    SELECT COUNT(*) FROM athletes 
                    WHERE {col} IS NULL
                """).fetchone()[0]
            else:
                # String columns - check NULL, empty string, 'None'
                empty = conn.execute(f"""
                    SELECT COUNT(*) FROM athletes 
                    WHERE {col} IS NULL OR {col} = '' OR {col} = 'None'
                """).fetchone()[0]
            filled = total - empty
            pct = (filled / total * 100) if total > 0 else 0
            print(f"{col:15} | Terisi: {filled:7,} ({pct:5.1f}%) | Kosong: {empty:7,}")
        
        # Cek unique values untuk reference
        print("\n\nUnique values per kolom:")
        for col in columns:
            if col == 'arrows':
                # Integer column - only check NULL
                unique = conn.execute(f"""
                    SELECT DISTINCT {col} FROM athletes 
                    WHERE {col} IS NOT NULL
                    ORDER BY {col}
                    LIMIT 30
                """).fetchall()
            else:
                # String columns - check NULL, empty string, 'None'
                unique = conn.execute(f"""
                    SELECT DISTINCT {col} FROM athletes 
                    WHERE {col} IS NOT NULL AND {col} != '' AND {col} != 'None'
                    ORDER BY {col}
                    LIMIT 30
                """).fetchall()
            print(f"\n{col} ({len(unique)} unique values):")
            for val in unique:
                print(f"  - {val[0]}")
            
    finally:
        conn.close()

if __name__ == "__main__":
    check_empty_columns()
