import os
import logging
import pandas as pd
from typing import List, Dict, Any

logger = logging.getLogger("IanseoScraper.DataHandler")

class IanseoDataHandler:
    """
    Mengelola pembersihan data, konversi tipe data, serta eksportasi ke berbagai format
    penyimpanan terstruktur seperti CSV, Excel, dan JSON menggunakan Pandas.
    """

    @staticmethod
    def create_dataframe(records: List[Dict[str, Any]]) -> pd.DataFrame:
        """Membuat Pandas DataFrame dari raw records dan merapikan tipe data."""
        if not records:
            logger.warning("Data record kosong. Membuat DataFrame kosong.")
            return pd.DataFrame()

        df = pd.DataFrame(records)
        
        # Pembersihan dan standardisasi tipe data
        try:
            # Numeric conversions
            df["rank"] = pd.to_numeric(df["rank"], errors="coerce").fillna(0).astype(int)
            df["total_score"] = pd.to_numeric(df["total_score"], errors="coerce").fillna(0).astype(int)
            df["tens"] = pd.to_numeric(df["tens"], errors="coerce").fillna(0).astype(int)
            df["xs"] = pd.to_numeric(df["xs"], errors="coerce").fillna(0).astype(int)
            df["arrows"] = pd.to_numeric(df["arrows"], errors="coerce").fillna(0).astype(int)
            
            # Distance columns - values may be "319/ 1" (score/rank), extract score part
            for col in ["distance_1", "distance_2", "distance_3", "distance_4", "distance_5", "distance_6", "distance_7", "distance_8", "distance_9", "distance_10"]:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.split("/").str[0].str.strip()
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
            
            # Index as float
            if "index" in df.columns:
                df["index"] = pd.to_numeric(df["index"], errors="coerce").fillna(0.0).round(3)
            
            # Urutkan berdasarkan kategori kemudian total score tertinggi
            df = df.sort_values(by=["category", "total_score"], ascending=[True, False])
            
        except Exception as e:
            logger.warning(f"Peringatan saat merapikan tipe data DataFrame: {e}")
            
        return df

    @staticmethod
    def export_data(df: pd.DataFrame, base_filename: str, formats: List[str] = ["csv", "xlsx"]) -> Dict[str, str]:
        """
        Mengekspor DataFrame ke file CSV, Excel, atau JSON.
        
        Args:
            df (pd.DataFrame): Data atlet dan skor.
            base_filename (str): Nama dasar file output (tanpa ekstensi).
            formats (List[str]): List format target (csv, xlsx, json).
            
        Returns:
            Dict[str, str]: Path dari file-file yang berhasil dibuat.
        """
        exported_files = {}
        if df.empty:
            logger.error("DataFrame kosong. Ekspor dibatalkan.")
            return exported_files

        # Pastikan direktori output tersedia
        output_dir = "output_data"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        full_base_path = os.path.join(output_dir, base_filename)

        if "csv" in formats:
            csv_path = f"{full_base_path}.csv"
            df.to_csv(csv_path, index=False, encoding="utf-8")
            logger.info(f"Data berhasil diekspor ke CSV: {csv_path}")
            exported_files["csv"] = csv_path

        if "xlsx" in formats or "excel" in formats:
            excel_path = f"{full_base_path}.xlsx"
            # Menggunakan excel writer dengan openpyxl engine
            with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
                # Simpan semua data di sheet utama
                df.to_excel(writer, sheet_name="All Results", index=False)
                
                # Tambahkan sheet terpisah per kategori untuk kemudahan analisis
                categories = df["category"].unique()
                for cat in categories:
                    # Filter data per kategori, hilangkan karakter khusus untuk nama sheet
                    sheet_name = str(cat)[:30].replace("/", "-").replace("*", "").replace("?", "")
                    cat_df = df[df["category"] == cat]
                    cat_df.to_excel(writer, sheet_name=sheet_name, index=False)
                    
            logger.info(f"Data berhasil diekspor ke Multi-Sheet Excel: {excel_path}")
            exported_files["excel"] = excel_path

        if "json" in formats:
            json_path = f"{full_base_path}.json"
            df.to_json(json_path, orient="records", indent=4, force_ascii=False)
            logger.info(f"Data berhasil diekspor ke JSON: {json_path}")
            exported_files["json"] = json_path

        return exported_files
