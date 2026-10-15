"""
Script untuk export records dengan arrows kosong ke CSV.
"""
import duckdb
import pandas as pd
from db_handler import ArcheryDatabase

def export_empty_arrows():
    """Export records dengan arrows kosong ke CSV."""
    db = ArcheryDatabase()
    conn = duckdb.connect(str(db.db_path))
    
    try:
        # Export records dengan arrows kosong
        df = conn.execute("""
            SELECT a.id, t.event_name, t.year, a.category, a.division, a.distance, a.gender, a.arrows
            FROM athletes a
            LEFT JOIN tournaments t ON a.event_id = t.event_id
            WHERE a.arrows = 0 OR a.arrows IS NULL
            ORDER BY t.event_name, t.year, a.category
        """).df()
        
        if df.empty:
            print("Tidak ada records dengan arrows kosong.")
            return
        
        print(f"Exporting {len(df)} records dengan arrows kosong...")
        
        # Export ke CSV
        output_file = "empty_arrows_export.csv"
        df.to_csv(output_file, index=False, sep=";", encoding='utf-8-sig')
        print(f"Exported to: {output_file}")
        
        # Tampilkan sample
        print("\nSample data:")
        print(df.head(10).to_string())
        
    finally:
        conn.close()

if __name__ == "__main__":
    export_empty_arrows()
