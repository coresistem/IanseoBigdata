import os
import logging
import requests
import pdfplumber
from typing import List, Dict, Any, Optional

logger = logging.getLogger("IanseoScraper.PDFParser")

class IanseoPDFExtractor:
    """
    Fungsi opsional dan tangguh untuk mengekstrak data dari dokumen hasil Ianseo berbentuk PDF.
    Sangat berguna jika hasil resmi turnamen hanya disediakan dalam bentuk PDF.
    """

    def __init__(self, download_dir: str = "downloaded_results"):
        self.download_dir = download_dir
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
            logger.info(f"Membuat folder download PDF: {download_dir}")

    def download_pdf(self, pdf_url: str, filename: str) -> Optional[str]:
        """Mengunduh file PDF hasil turnamen dari server Ianseo."""
        local_path = os.path.join(self.download_dir, filename)
        
        try:
            logger.info(f"Mengunduh PDF dari: {pdf_url}")
            response = requests.get(pdf_url, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(local_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logger.info(f"PDF berhasil diunduh dan disimpan di: {local_path}")
            return local_path
        except Exception as e:
            logger.error(f"Gagal mengunduh file PDF {pdf_url}: {e}")
            return None

    def extract_table_from_pdf(self, pdf_path: str, category_name: str) -> List[Dict[str, Any]]:
        """
        Mengekstrak tabel hasil pertandingan dari file PDF menggunakan 'pdfplumber'.
        
        Args:
            pdf_path (str): Path lokal file PDF.
            category_name (str): Nama kategori target (misal: 'Recurve Men').
            
        Returns:
            List[Dict[str, Any]]: List dictionary data atlet yang diekstrak.
        """
        records = []
        if not os.path.exists(pdf_path):
            logger.error(f"File PDF tidak ditemukan: {pdf_path}")
            return records

        logger.info(f"Membuka file PDF untuk parsing: {pdf_path}")
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    logger.info(f"Menganalisis PDF Halaman {page_num + 1}...")
                    
                    # Ekstrak tabel terstruktur dari halaman
                    tables = page.extract_tables()
                    
                    for table in tables:
                        if not table or len(table) < 2:
                            continue
                            
                        # Cari indeks kolom berdasarkan nama kolom di baris pertama/kedua
                        header = [str(cell).strip().lower() for col in table[:2] for cell in col if cell]
                        
                        # Cek apakah tabel ini adalah tabel hasil skor (memiliki Rank/Pos/Name/Athlete)
                        if not any(h in header for h in ["rank", "pos", "athlete", "name", "atlet"]):
                            # Lewati jika bukan tabel hasil (misal tabel logistik, jadwal, dll)
                            continue

                        # Bersihkan header
                        clean_header = [str(cell).replace("\\n", " ").strip() for cell in table[0]]
                        
                        # Parsing baris data di bawah header
                        for row in table[1:]:
                            # Abaikan baris kosong atau tidak lengkap
                            if not row or len(row) < 4:
                                continue
                                
                            # Lewati jika baris ini berisi teks duplikat header
                            if str(row[0]).lower() in ["rank", "pos", "position"]:
                                continue
                                
                            try:
                                # Ekstrak kolom utama secara fleksibel
                                # Kolom 0 biasanya Rank, Kolom 1 Bib/BackNo, Kolom 2 Nama, Kolom 3 Club/Country
                                athlete_name = str(row[2]).replace("\\n", " ").strip() if len(row) > 2 else ""
                                club = str(row[3]).replace("\\n", " ").strip() if len(row) > 3 else ""
                                
                                # Deteksi total skor dan 10s/Xs dari kolom-kolom belakang
                                total_val = "0"
                                tens_val = "0"
                                xs_val = "0"
                                
                                # Mengingat struktur PDF bervariasi, kita ambil angka-angka di kolom terakhir
                                numeric_cols = [str(c).strip() for c in row[4:] if c and str(c).strip().replace("-", "").isdigit()]
                                if len(numeric_cols) >= 3:
                                    # Biasanya format: [Jarak1, Jarak2, Total, 10s, Xs]
                                    total_val = numeric_cols[-3]
                                    tens_val = numeric_cols[-2]
                                    xs_val = numeric_cols[-1]
                                elif len(numeric_cols) == 1:
                                    total_val = numeric_cols[0]

                                if athlete_name and athlete_name != "None":
                                    atlet_data = {
                                        "rank": str(row[0]).strip(),
                                        "back_no": str(row[1]).strip() if len(row) > 1 else "",
                                        "athlete_name": athlete_name,
                                        "club_provinsi": club,
                                        "distance_1": numeric_cols[0] if len(numeric_cols) > 2 else "0",
                                        "distance_2": numeric_cols[1] if len(numeric_cols) > 3 else "0",
                                        "total_score": total_val,
                                        "tens": tens_val,
                                        "xs": xs_val,
                                        "category": category_name,
                                        "round": "Qualification (PDF-Extracted)"
                                    }
                                    records.append(atlet_data)
                            except Exception as row_err:
                                logger.warning(f"Gagal memparsing baris PDF: {row_err}")
                                
            logger.info(f"Ekstraksi PDF Selesai. Total diekstrak: {len(records)} Atlet.")
            
        except Exception as e:
            logger.error(f"Error fatal saat mengekstrak tabel dari PDF: {e}")
            
        return records
