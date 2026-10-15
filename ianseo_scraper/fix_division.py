"""
Script untuk mengisi kolom division yang kosong berdasarkan parsing kolom category.
"""
import re
import duckdb
from db_handler import ArcheryDatabase

def parse_division_from_category(category_name: str) -> str:
    """Extract division dari category name."""
    if not category_name:
        return ""
    
    cat_upper = category_name.upper()
    
    # Division priorities (standar + lokal Indonesia)
    for div in ["NASIONAL", "RECURVE", "COMPOUND", "BAREBOW", "PARALON", "STANDARD", "PIN"]:
        if div in cat_upper:
            return div
    
    return ""

def fix_empty_divisions():
    """Update records dengan division kosong menggunakan parsing dari category."""
    db = ArcheryDatabase()
    conn = duckdb.connect(str(db.db_path))
    
    try:
        # Fix Gender: putri -> Women, putra -> Men (from existing gender values)
        print("Memperbaiki Gender yang sudah ada...")
        conn.execute("""
            UPDATE athletes 
            SET gender = CASE
                WHEN UPPER(gender) LIKE '%PUTRI%' OR UPPER(gender) LIKE '%WANITA%' OR UPPER(gender) LIKE '%FEMALE%' THEN 'Women'
                WHEN UPPER(gender) LIKE '%PUTRA%' OR UPPER(gender) LIKE '%PRIA%' OR UPPER(gender) LIKE '%MALE%' THEN 'Men'
                WHEN UPPER(gender) LIKE '%CAMPURAN%' OR UPPER(gender) LIKE '%MIXED%' THEN 'Mixed'
                ELSE gender
            END
            WHERE gender IS NOT NULL AND gender != '' AND gender != 'None'
        """)
        
        # Fill empty gender from category
        print("Mengisi Gender kosong dari category...")
        conn.execute("""
            UPDATE athletes 
            SET gender = CASE
                WHEN UPPER(category) LIKE '%PUTRI%' OR UPPER(category) LIKE '%WANITA%' OR UPPER(category) LIKE '%WOMEN%' OR UPPER(category) LIKE '%FEMALE%' OR UPPER(category) LIKE '%WOMAN%' OR UPPER(category) LIKE '%GIRL%' OR UPPER(category) LIKE '%W$' THEN 'Women'
                WHEN UPPER(category) LIKE '%PUTRA%' OR UPPER(category) LIKE '%PRIA%' OR UPPER(category) LIKE '%MEN%' OR UPPER(category) LIKE '%MALE%' OR UPPER(category) LIKE '%BOY%' OR UPPER(category) LIKE '%MAN%' THEN 'Men'
                WHEN UPPER(category) LIKE '%CAMPURAN%' OR UPPER(category) LIKE '%MIXED%' THEN 'Mixed'
                ELSE gender
            END
            WHERE (gender IS NULL OR gender = '' OR gender = 'None')
              AND (
                  UPPER(category) LIKE '%PUTRI%' OR UPPER(category) LIKE '%WANITA%' OR UPPER(category) LIKE '%WOMEN%' OR UPPER(category) LIKE '%FEMALE%' OR UPPER(category) LIKE '%WOMAN%' OR UPPER(category) LIKE '%GIRL%' OR UPPER(category) LIKE '%W$' OR
                  UPPER(category) LIKE '%PUTRA%' OR UPPER(category) LIKE '%PRIA%' OR UPPER(category) LIKE '%MEN%' OR UPPER(category) LIKE '%MALE%' OR UPPER(category) LIKE '%BOY%' OR UPPER(category) LIKE '%MAN%' OR
                  UPPER(category) LIKE '%CAMPURAN%' OR UPPER(category) LIKE '%MIXED%'
              )
        """)
        
        # Check gender stats
        gender_filled = conn.execute("SELECT COUNT(*) FROM athletes WHERE gender IS NOT NULL AND gender != '' AND gender != 'None'").fetchone()[0]
        gender_empty = conn.execute("SELECT COUNT(*) FROM athletes WHERE gender IS NULL OR gender = '' OR gender = 'None'").fetchone()[0]
        print(f"Gender terisi: {gender_filled}, Gender kosong: {gender_empty}")
        
        # Check sample categories with empty gender
        if gender_empty > 0:
            print("\nSample category dengan gender kosong:")
            cat_samples = conn.execute("""
                SELECT DISTINCT category 
                FROM athletes 
                WHERE gender IS NULL OR gender = '' OR gender = 'None'
                LIMIT 20
            """).fetchall()
            for cat in cat_samples:
                print(f"  - {cat[0]}")
        
        # Fix Division case: Bare bow -> Barebow, etc
        print("Memperbaiki case Division...")
        conn.execute("""
            UPDATE athletes 
            SET division = CASE
                WHEN UPPER(division) LIKE '%BARE BOW%' THEN 'Barebow'
                WHEN UPPER(division) LIKE '%STANDAR BOW%' THEN 'Standard'
                WHEN UPPER(division) LIKE '%NATIONAL%' THEN 'Nasional'
                ELSE division
            END
            WHERE division IS NOT NULL AND division != '' AND division != 'None'
        """)
        
        # Fix distance anomaly
        print("Memperbaiki distance anomaly...")
        conn.execute("""
            UPDATE athletes 
            SET distance = '30-40-50m'
            WHERE distance = '304050m'
        """)
        conn.execute("""
            UPDATE athletes 
            SET distance = '5-8-12-15m'
            WHERE distance = '581215m'
        """)
        print("Distance anomaly fixed: 304050m -> 30-40-50m, 581215m -> 5-8-12-15m")
        
        # Fix arrows from category (Indonesian: "Anak Panah", English: "Arrows")
        print("Memperbaiki arrows dari category...")
        
        # Debug: cek sample category dengan arrows=0
        samples = conn.execute("""
            SELECT DISTINCT category, distance 
            FROM athletes 
            WHERE arrows = 0 OR arrows IS NULL
            LIMIT 10
        """).fetchall()
        print("Sample category dengan arrows=0:")
        for cat, dist in samples:
            print(f"  - {cat} | Distance: {dist}")
        
        # Fetch records with arrows = 0 or NULL
        records = conn.execute("""
            SELECT id, category 
            FROM athletes 
            WHERE arrows = 0 OR arrows IS NULL
        """).fetchall()
        
        updated = 0
        for record_id, category in records:
            if not category:
                continue
            
            cat_upper = category.upper()
            arrows_val = 0
            
            # Extract arrows from Indonesian pattern
            m = re.search(r'(\d+)\s*ANAK PANAH', cat_upper)
            if m:
                arrows_val = int(m.group(1))
            # Extract arrows from English pattern
            else:
                m = re.search(r'(\d+)\s*ARROWS?', cat_upper)
                if m:
                    arrows_val = int(m.group(1))
            
            if arrows_val > 0:
                conn.execute("""
                    UPDATE athletes 
                    SET arrows = ? 
                    WHERE id = ?
                """, [arrows_val, record_id])
                updated += 1
        
        # Infer arrows from distance for remaining records
        print("Menginfer arrows dari distance...")
        conn.execute("""
            UPDATE athletes 
            SET arrows = CASE
                WHEN distance IN ('18m', '25m') THEN 30  -- Indoor distances
                WHEN distance IN ('3m', '4m', '5m', '6m', '7m', '8m', '9m', '10m', '11m', '12m', '13m', '15m', '16m', '17m', '19m', '20m', '21m') THEN 36
                WHEN distance IN ('30m', '40m', '50m', '60m', '70m', '90m') THEN 36
                WHEN distance = '70m' AND (category LIKE '%72%' OR category LIKE '%144%') THEN 72
                WHEN distance = '70m' THEN 72
                WHEN distance IN ('50m', '60m', '70m', '90m') AND category LIKE '%144%' THEN 144
                WHEN distance LIKE '%-%' THEN 36  -- Multi-distance like 30-40-50m
                ELSE arrows
            END
            WHERE (arrows = 0 OR arrows IS NULL) AND distance IS NOT NULL AND distance != ''
        """)
        
        print(f"Arrows diperbarui: {updated} records")
        
        arrows_updated = conn.execute("SELECT COUNT(*) FROM athletes WHERE arrows > 0").fetchone()[0]
        arrows_zero = conn.execute("SELECT COUNT(*) FROM athletes WHERE arrows = 0 OR arrows IS NULL").fetchone()[0]
        print(f"Arrows terisi: {arrows_updated}, Arrows kosong/0: {arrows_zero}")
        
        # Cek berapa banyak record dengan division kosong
        result = conn.execute("""
            SELECT COUNT(*) FROM athletes 
            WHERE division IS NULL OR division = '' OR division = 'None'
        """).fetchone()
        empty_count = result[0]
        print(f"Records dengan division kosong: {empty_count}")
        
        if empty_count == 0:
            print("Tidak ada record dengan division kosong.")
            return
        
        # Ambil sample untuk preview
        sample = conn.execute("""
            SELECT id, category, division 
            FROM athletes 
            WHERE division IS NULL OR division = '' OR division = 'None'
            LIMIT 10
        """).fetchall()
        print("\nSample records:")
        for row in sample:
            print(f"  ID: {row[0]}, Category: {row[1]}, Division: {row[2]}")
        
        # Update division berdasarkan category (single statement)
        print("\nMemulai update...")
        
        conn.execute("""
            UPDATE athletes 
            SET division = CASE
                WHEN UPPER(category) LIKE '%NASIONAL%' OR UPPER(category) LIKE '%NASIOAL%' THEN 'NASIONAL'
                WHEN UPPER(category) LIKE '%RECURVE%' OR UPPER(category) LIKE '%RECUVE%' THEN 'RECURVE'
                WHEN UPPER(category) LIKE '%COMPOUND%' THEN 'COMPOUND'
                WHEN UPPER(category) LIKE '%BAREBOW%' OR UPPER(category) LIKE '%BB%' THEN 'BAREBOW'
                WHEN UPPER(category) LIKE '%PARALON%' THEN 'PARALON'
                WHEN UPPER(category) LIKE '%STANDARD%' OR UPPER(category) LIKE '%STANDAR%' OR UPPER(category) LIKE '%STANDARBOW%' OR UPPER(category) LIKE '%STD BOW%' OR UPPER(category) LIKE '%STDBOW%' OR UPPER(category) LIKE '%STD%' THEN 'STANDARD'
                WHEN UPPER(category) LIKE '%PIN%' THEN 'PIN'
                WHEN UPPER(category) LIKE '%TRADITIONAL%' OR UPPER(category) LIKE '%TRADBOW%' OR UPPER(category) LIKE '%TRADISIONAL%' THEN 'TRADITIONAL'
                WHEN UPPER(category) LIKE '%PERPANI%' THEN 'PERPANI'
                WHEN UPPER(category) LIKE '%HORSEBOW%' THEN 'HORSEBOW'
                WHEN UPPER(category) LIKE '%GENERAL%' THEN 'GENERAL'
                WHEN UPPER(category) LIKE '%PVC%' THEN 'PVC'
                WHEN UPPER(category) LIKE '%PEMULA%' THEN 'PEMULA'
                WHEN UPPER(category) LIKE '%PRESTASI%' THEN 'PRESTASI'
                WHEN UPPER(category) LIKE '%DEWASA%' THEN 'DEWASA'
                WHEN UPPER(category) LIKE '%EKSEKUTIF%' OR UPPER(category) LIKE '%KARYAWAN%' THEN 'EKSEKUTIF'
                WHEN UPPER(category) LIKE '%PELAJAR%' THEN 'PELAJAR'
                WHEN UPPER(category) LIKE '%MAHASISWA%' THEN 'MAHASISWA'
                WHEN UPPER(category) LIKE '%PIA%' THEN 'PIA'
                WHEN UPPER(category) LIKE '%SN%' THEN 'SN'
                WHEN UPPER(category) LIKE '%UMUM%' THEN 'UMUM'
                WHEN UPPER(category) LIKE '%FUN%' THEN 'FUN'
                WHEN UPPER(category) LIKE '%BUM%' THEN 'BUM'
                WHEN UPPER(category) LIKE '%ELEMENTARY%' THEN 'ELEMENTARY'
                WHEN UPPER(category) LIKE '%ALL IN ONE%' THEN 'ALL IN ONE'
                ELSE division
            END
            WHERE (division IS NULL OR division = '' OR division = 'None')
              AND (
                  UPPER(category) LIKE '%NASIONAL%' OR UPPER(category) LIKE '%NASIOAL%' OR
                  UPPER(category) LIKE '%RECURVE%' OR UPPER(category) LIKE '%RECUVE%' OR
                  UPPER(category) LIKE '%COMPOUND%' OR
                  UPPER(category) LIKE '%BAREBOW%' OR UPPER(category) LIKE '%BB%' OR
                  UPPER(category) LIKE '%PARALON%' OR
                  UPPER(category) LIKE '%STANDARD%' OR UPPER(category) LIKE '%STANDAR%' OR UPPER(category) LIKE '%STANDARBOW%' OR UPPER(category) LIKE '%STD BOW%' OR UPPER(category) LIKE '%STDBOW%' OR UPPER(category) LIKE '%STD%' OR
                  UPPER(category) LIKE '%PIN%' OR
                  UPPER(category) LIKE '%TRADITIONAL%' OR UPPER(category) LIKE '%TRADBOW%' OR UPPER(category) LIKE '%TRADISIONAL%' OR
                  UPPER(category) LIKE '%PERPANI%' OR
                  UPPER(category) LIKE '%HORSEBOW%' OR
                  UPPER(category) LIKE '%GENERAL%' OR
                  UPPER(category) LIKE '%PVC%' OR
                  UPPER(category) LIKE '%PEMULA%' OR
                  UPPER(category) LIKE '%PRESTASI%' OR
                  UPPER(category) LIKE '%DEWASA%' OR
                  UPPER(category) LIKE '%EKSEKUTIF%' OR UPPER(category) LIKE '%KARYAWAN%' OR
                  UPPER(category) LIKE '%PELAJAR%' OR
                  UPPER(category) LIKE '%MAHASISWA%' OR
                  UPPER(category) LIKE '%PIA%' OR
                  UPPER(category) LIKE '%SN%' OR
                  UPPER(category) LIKE '%UMUM%' OR
                  UPPER(category) LIKE '%FUN%' OR
                  UPPER(category) LIKE '%BUM%' OR
                  UPPER(category) LIKE '%ELEMENTARY%' OR
                  UPPER(category) LIKE '%ALL IN ONE%'
              )
        """)
        
        updated = conn.execute("SELECT COUNT(*) FROM athletes WHERE division IS NOT NULL AND division != '' AND division != 'None'").fetchone()[0]
        print(f"Total records dengan division terisi: {updated}")
        
        # Cek sisa division kosong
        remaining = conn.execute("""
            SELECT COUNT(*) FROM athletes 
            WHERE division IS NULL OR division = '' OR division = 'None'
        """).fetchone()[0]
        print(f"Sisa division kosong: {remaining}")
        
        # Cek unique category yang masih kosong divisionnya
        if remaining > 0:
            print("\nSample category yang masih kosong division:")
            categories = conn.execute("""
                SELECT DISTINCT category 
                FROM athletes 
                WHERE division IS NULL OR division = '' OR division = 'None'
                LIMIT 20
            """).fetchall()
            for cat in categories:
                print(f"  - {cat[0]}")
        
    finally:
        conn.close()

if __name__ == "__main__":
    fix_empty_divisions()
