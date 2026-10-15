export interface PythonFile {
  name: string;
  language: string;
  description: string;
  content: string;
}

export const pythonCodebase: PythonFile[] = [
  {
    name: "requirements.txt",
    language: "text",
    description: "Daftar dependensi Python yang dibutuhkan untuk menjalankan engine scraper.",
    content: `requests>=2.31.0
beautifulsoup4>=4.12.0
pandas>=2.0.0
pdfplumber>=0.10.0
lxml>=4.9.0
colorama>=0.4.6
openpyxl>=3.1.0
`
  },
  {
    name: "scraper_engine.py",
    language: "python",
    description: "Modul inti untuk scraping, menangani request HTTP, rotasi User-Agent, delay dinamis, dan ekstraksi HTML.",
    content: `import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Any

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("ianseo_scraper.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("IanseoScraper")

class IanseoScraperEngine:
    """
    Engine utama untuk melakukan koneksi dan scraping ke situs Ianseo.
    Dilengkapi dengan rotasi User-Agent, rate-limiting dinamis, dan penanganan error robust.
    """
    
    BASE_URL = "https://www.ianseo.net"
    
    # List User-Agent untuk menghindari blocking / anti-scraping
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
    ]

    def __init__(self, delay_range: tuple = (1.0, 3.0), timeout: int = 15):
        """
        Args:
            delay_range (tuple): Batas min & max jeda waktu (detik) antar request.
            timeout (int): Batas waktu request HTTP sebelum dianggap timeout.
        """
        self.session = requests.Session()
        self.delay_range = delay_range
        self.timeout = timeout
        
    def _get_headers(self) -> Dict[str, str]:
        """Menghasilkan headers dengan User-Agent acak untuk request."""
        return {
            "User-Agent": random.choice(self.USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "id,en-US;q=0.7,en;q=0.3",
            "Referer": self.BASE_URL,
            "Connection": "keep-alive"
        }

    def fetch_page(self, url: str, params: Optional[Dict[str, Any]] = None) -> Optional[BeautifulSoup]:
        """
        Melakukan HTTP GET request ke URL yang dituju dengan penanganan error.
        Menerapkan dynamic delay untuk scraping beretika.
        """
        # Delay dinamis sebelum request
        sleep_time = random.uniform(self.delay_range[0], self.delay_range[1])
        logger.debug(f"Menunggu {sleep_time:.2f} detik sebelum request ke {url}...")
        time.sleep(sleep_time)

        # Ubah URL jika relatif
        full_url = url if url.startswith("http") else f"{self.BASE_URL}/{url.lstrip('/')}"
        
        try:
            logger.info(f"Mengirim request ke: {full_url}")
            response = self.session.get(
                full_url, 
                params=params, 
                headers=self._get_headers(), 
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # Gunakan lxml parser jika tersedia, fallback ke html.parser
            try:
                soup = BeautifulSoup(response.text, "lxml")
            except Exception:
                soup = BeautifulSoup(response.text, "html.parser")
                
            return soup
            
        except requests.exceptions.Timeout:
            logger.error(f"Request Timeout saat mengakses {full_url}")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error {response.status_code} pada {full_url}: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Koneksi gagal pada {full_url}: {e}")
        return None

    def scrape_indonesian_events(self) -> List[Dict[str, Any]]:
        """
        LEVEL 1: Mengambil daftar turnamen dari Indonesia.
        URL Target: TourList.php?countryid=INA
        """
        target_url = "TourList.php"
        params = {"countryid": "INA"}
        
        soup = self.fetch_page(target_url, params=params)
        events = []
        
        if not soup:
            logger.error("Gagal mendapatkan daftar event Indonesia.")
            return events

        # Ianseo biasanya menaruh daftar turnamen di dalam tabel dengan class 'display' atau langsung <table>
        table = soup.find("table", {"class": "display"}) or soup.find("table")
        if not table:
            logger.warning("Tabel turnamen tidak ditemukan di halaman. Mencoba mencari tag <tr>.")
            table = soup # Coba cari langsung di root soup
            
        rows = table.find_all("tr") if table else []
        logger.info(f"Ditemukan {len(rows)} baris data potensial.")

        for row in rows:
            # Lewati baris header jika ada tag <th>
            if row.find("th"):
                continue
                
            cols = row.find_all("td")
            if len(cols) >= 4:
                try:
                    # Parsing data dasar dari kolom
                    # Ianseo standard columns: [ID/Logo, Nama Turnamen, Tanggal, Lokasi]
                    link_tag = cols[1].find("a")
                    if not link_tag:
                        continue
                        
                    event_url = link_tag.get("href", "")
                    # Ambil ID Event dari URL (misal: Tournament.php?id=12345 atau Tournament.php?Id=12345)
                    event_id = ""
                    if "id=" in event_url.lower():
                        # split by id= atau Id= atau ID=
                        parts = event_url.split("?")[-1].split("&")
                        for p in parts:
                            if p.lower().startswith("id="):
                                event_id = p.split("=")[-1]
                                break

                    event_name = link_tag.get_text(strip=True)
                    date_val = cols[2].get_text(strip=True)
                    location_val = cols[3].get_text(strip=True)
                    
                    event_data = {
                        "event_id": event_id,
                        "event_name": event_name,
                        "date": date_val,
                        "location": location_val,
                        "detail_url": event_url
                    }
                    events.append(event_data)
                    logger.info(f"Sukses Ekstrak Event: [{event_id}] {event_name}")
                except Exception as e:
                    logger.error(f"Gagal memparsing baris event: {e}")
                    
        return events
`
  },
  {
    name: "parser_engine.py",
    language: "python",
    description: "Modul parsing HTML untuk Level 2 (Navigasi menu hasil) dan Level 3 (Parsing tabel hasil atlet dan skor).",
    content: `import re
import logging
from bs4 import BeautifulSoup
from typing import Dict, List, Any, Optional

logger = logging.getLogger("IanseoScraper.Parser")

class IanseoParser:
    """
    Parser khusus untuk memahami struktur markup halaman Ianseo yang sangat dinamis.
    Mengekstrak menu hasil, kategori kompetisi, dan data skor atlet.
    """

    @staticmethod
    def extract_event_navigation(soup: BeautifulSoup) -> Dict[str, List[Dict[str, str]]]:
        """
        LEVEL 2: Memetakan menu link hasil (ResultList.php, Official.php, PDF Book, dll).
        Menganalisis link yang tersedia di sidebar atau modul menu event.
        """
        navigation_links = {
            "qualification_links": [],
            "elimination_links": [],
            "team_links": [],
            "pdf_documents": []
        }
        
        if not soup:
            return navigation_links

        # Temukan semua link di halaman
        all_links = soup.find_all("a")
        
        for link in all_links:
            href = link.get("href", "")
            text = link.get_text(strip=True)
            
            if not href:
                continue
                
            link_info = {"text": text, "url": href}
            
            # Analisis tipe link berdasarkan nama file & query string
            if "ResultList.php" in href or "Result.php" in href:
                # Biasanya ini link hasil kualifikasi individu
                navigation_links["qualification_links"].append(link_info)
                
            elif "Official.php" in href:
                # Link hasil resmi / eliminasi
                if "elim" in href.lower() or "bracket" in href.lower() or "head" in href.lower():
                    navigation_links["elimination_links"].append(link_info)
                else:
                    navigation_links["qualification_links"].append(link_info)
                    
            elif "Team" in href or "ResultTeam" in href:
                navigation_links["team_links"].append(link_info)
                
            elif href.endswith(".pdf") or "Book.php" in href or "PDF" in text.upper():
                navigation_links["pdf_documents"].append(link_info)
                
        logger.info(
            f"Selesai memetakan link detail. Hasil: "
            f"{len(navigation_links['qualification_links'])} Kualifikasi, "
            f"{len(navigation_links['elimination_links'])} Eliminasi, "
            f"{len(navigation_links['pdf_documents'])} PDF"
        )
        return navigation_links

    @staticmethod
    def parse_scores_table(soup: BeautifulSoup, category_name: str, round_type: str = "Qualification") -> List[Dict[str, Any]]:
        """
        LEVEL 3: Ekstraksi Tabel Hasil Atlet & Skor.
        Menganalisis tabel skor Ianseo yang memiliki pola kolom berulang (Jarak 1, Jarak 2, dst).
        """
        records = []
        if not soup:
            return records

        # Cari tabel data utama. Ianseo biasanya menaruh data di tabel dengan class 'grid', 'display', 'tableVal' atau 'table'
        table = (
            soup.find("table", {"class": "grid"}) or 
            soup.find("table", {"class": "display"}) or 
            soup.find("table", {"class": "tableVal"}) or
            soup.find("table")
        )
        
        if not table:
            logger.warning("Tabel hasil skor tidak ditemukan di halaman HTML.")
            return records

        rows = table.find_all("tr")
        if not rows:
            return records

        # Identifikasi header tabel untuk pemetaan kolom dinamis
        header_cols = []
        header_row = None
        
        # Cari baris yang mengandung th atau baris pertama dengan class header/caption
        for row in rows:
            th_tags = row.find_all(["th", "td"])
            th_texts = [th.get_text(strip=True).lower() for th in th_tags]
            
            # Deteksi apakah baris ini adalah baris header (mengandung kolom nama/athlete/rank)
            if any(h in th_texts for h in ["rank", "pos.", "athlete", "atlet", "nama", "name"]):
                header_row = row
                header_cols = [t.get_text(strip=True) for t in th_tags]
                break
                
        # Jika tidak ditemukan header secara eksplisit, gunakan index default
        if not header_cols:
            logger.warning("Header tabel tidak terdeteksi secara otomatis. Menggunakan estimasi posisi kolom.")
            # Default header mapping untuk Ianseo
            header_cols = ["Rank", "BackNo", "Athlete", "Country", "Distance1", "Distance2", "Total", "10s", "Xs"]

        logger.info(f"Struktur header terdeteksi: {header_cols}")

        # Mulai parsing baris data
        for row in rows:
            # Lewati baris header
            if row == header_row:
                continue
                
            cols = row.find_all("td")
            if not cols:
                continue
                
            # Jika baris adalah pembatas/spacer (biasanya kosong atau berisi info kategori tambahan)
            if len(cols) < 4:
                continue

            # Bersihkan teks di setiap kolom
            row_data = [col.get_text(strip=True) for col in cols]
            
            try:
                # Buat dictionary penampung data atlet
                atlet_info = {
                    "rank": "",
                    "back_no": "",
                    "athlete_name": "",
                    "club_provinsi": "",
                    "distance_1": "0",
                    "distance_2": "0",
                    "total_score": "0",
                    "tens": "0",
                    "xs": "0",
                    "category": category_name,
                    "round": round_type
                }

                # Pemetaan kolom cerdas berdasarkan kecocokan nama kolom header
                for idx, col_text in enumerate(row_data):
                    if idx >= len(header_cols):
                        break
                        
                    header_name = header_cols[idx].lower()
                    
                    # Pemetaan Rank
                    if header_name in ["rank", "pos.", "no"]:
                        atlet_info["rank"] = col_text
                    # Pemetaan Nomor Punggung / Target
                    elif header_name in ["backno", "backno.", "target", "bib"]:
                        atlet_info["back_no"] = col_text
                    # Pemetaan Nama Atlet
                    elif header_name in ["athlete", "atlet", "name", "nama atlet", "nama"]:
                        atlet_info["athlete_name"] = col_text
                    # Pemetaan Club / Country
                    elif header_name in ["country", "club", "provinsi", "prov", "sas"]:
                        atlet_info["club_provinsi"] = col_text
                    # Pemetaan Total Skor
                    elif header_name in ["total", "tot", "score", "skor"]:
                        atlet_info["total_score"] = col_text
                    # Pemetaan Jumlah 10s
                    elif header_name in ["10", "10s", "10's", "10s/xs"]:
                        # Kadang digabung '10s/Xs', kita tangani nanti jika ada splitter
                        atlet_info["tens"] = col_text
                    # Pemetaan Jumlah Xs
                    elif header_name in ["x", "xs", "x's"]:
                        atlet_info["xs"] = col_text
                    # Pemetaan Jarak (Jarak 1, Jarak 2)
                    elif "m-" in header_name or re.search(r"\\d+m", header_name) or "distance" in header_name or "dist" in header_name:
                        if atlet_info["distance_1"] == "0":
                            atlet_info["distance_1"] = col_text
                        else:
                            atlet_info["distance_2"] = col_text

                # Post-processing pembersihan data
                # Jika 10s dan Xs digabung di satu kolom (misal: "15 / 5")
                if "/" in atlet_info["tens"] and atlet_info["xs"] == "0":
                    parts = atlet_info["tens"].split("/")
                    atlet_info["tens"] = parts[0].strip()
                    atlet_info["xs"] = parts[1].strip() if len(parts) > 1 else "0"

                # Validasi minimal: Baris harus memiliki nama atlet dan total skor untuk disimpan
                if atlet_info["athlete_name"] and atlet_info["total_score"]:
                    records.append(atlet_info)
                    
            except Exception as e:
                logger.error(f"Error memparsing baris atlet: {e}, Data: {row_data}")

        logger.info(f"Berhasil memparsing {len(records)} baris atlet dari tabel.")
        return records
`
  },
  {
    name: "pdf_parser.py",
    language: "python",
    description: "Modul penanganan file PDF. Mengunduh dan mengekstrak tabel hasil turnamen menggunakan library 'pdfplumber'.",
    content: `import os
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
`
  },
  {
    name: "data_handler.py",
    language: "python",
    description: "Modul pemrosesan data menggunakan Pandas. Menyimpan hasil akhir ke Excel, CSV, atau JSON secara terstruktur.",
    content: `import os
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
            # Ubah rank, total, 10s, Xs menjadi numerik
            df["rank"] = pd.to_numeric(df["rank"], errors="coerce").fillna(0).astype(int)
            df["total_score"] = pd.to_numeric(df["total_score"], errors="coerce").fillna(0).astype(int)
            df["tens"] = pd.to_numeric(df["tens"], errors="coerce").fillna(0).astype(int)
            df["xs"] = pd.to_numeric(df["xs"], errors="coerce").fillna(0).astype(int)
            
            # Distance 1 & 2
            df["distance_1"] = pd.to_numeric(df["distance_1"], errors="coerce").fillna(0).astype(int)
            df["distance_2"] = pd.to_numeric(df["distance_2"], errors="coerce").fillna(0).astype(int)
            
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
`
  },
  {
    name: "main.py",
    language: "python",
    description: "File entry point utama program. Berupa CLI untuk menjalankan alur scraping secara otomatis.",
    content: `# -*- coding: utf-8 -*-
"""
Ianseo Archery Web Scraper Engine (CLI Entrypoint)
=================================================
Dibuat untuk mengekstrak data turnamen panahan dari ianseo.net secara komprehensif.
Mendukung Level 1 (Event List), Level 2 (Menu & Link Hasil), dan Level 3 (Parsing Skor & Atlet).

Menghargai Etika Scraping dengan dynamic delay dan rotasi User-Agent.
"""

import argparse
import sys
from scraper_engine import IanseoScraperEngine, logger
from parser_engine import IanseoParser
from pdf_parser import IanseoPDFExtractor
from data_handler import IanseoDataHandler

def run_scraping_workflow(event_id: str, delay_min: float, delay_max: float, run_pdf: bool):
    """Fungsi orkestrator yang menyatukan seluruh level scraping."""
    logger.info("=" * 60)
    logger.info(f"Memulai Alur Scraping Ianseo untuk ID Event: {event_id}")
    logger.info("=" * 60)

    # 1. Inisialisasi Engine
    engine = IanseoScraperEngine(delay_range=(delay_min, delay_max))
    all_extracted_records = []

    # 2. Ambil Informasi Detail Turnamen & Menu Hasil (LEVEL 2)
    detail_url = f"Tournament.php?id={event_id}"
    logger.info(f"[LANGKAH 1] Mengambil halaman detail turnamen...")
    detail_soup = engine.fetch_page(detail_url)
    
    if not detail_soup:
        logger.error(f"Gagal memuat detail turnamen ID: {event_id}. Proses dihentikan.")
        sys.exit(1)

    # Ekstrak judul event
    title_tag = detail_soup.find("h1") or detail_soup.find("h2") or detail_soup.find("title")
    event_name = title_tag.get_text(strip=True) if title_tag else f"Tournament_{event_id}"
    logger.info(f"Mulai Scraping Turnamen: {event_name}")

    # Map menu navigasi yang tersedia
    nav_links = IanseoParser.extract_event_navigation(detail_soup)

    # 3. Proses Hasil Kualifikasi / Eliminasi (LEVEL 3 - HTML Parsing)
    qualification_links = nav_links["qualification_links"]
    if qualification_links:
        logger.info(f"[LANGKAH 2] Menemukan {len(qualification_links)} link kualifikasi HTML. Mulai parsing...")
        for q_link in qualification_links[:5]: # Membatasi 5 pertama untuk demo / keselamatan server
            cat_name = q_link["text"]
            url = q_link["url"]
            
            logger.info(f"Mengekstrak Kategori: {cat_name}")
            page_soup = engine.fetch_page(url)
            if page_soup:
                records = IanseoParser.parse_scores_table(page_soup, category_name=cat_name, round_type="Qualification")
                all_extracted_records.extend(records)
    else:
        logger.warning("Tidak ditemukan link tabel hasil HTML langsung di halaman utama.")

    # 4. Penanganan Opsional / Alternatif: PDF Extraction (LEVEL 3 - PDF Parsing)
    if run_pdf and nav_links["pdf_documents"]:
        logger.info(f"[LANGKAH 3] Menemukan dokumen PDF hasil. Mengaktifkan Engine PDF Parser...")
        pdf_extractor = IanseoPDFExtractor()
        
        for pdf_link in nav_links["pdf_documents"][:2]: # Ambil maksimal 2 dokumen PDF utama untuk keselamatan
            pdf_url = pdf_link["url"]
            pdf_name = f"event_{event_id}_{pdf_link['text'].replace(' ', '_')}.pdf"
            
            # Unduh file PDF
            local_pdf_path = pdf_extractor.download_pdf(pdf_url, pdf_name)
            if local_pdf_path:
                # Ekstrak tabel dari PDF
                pdf_records = pdf_extractor.extract_table_from_pdf(local_pdf_path, category_name=pdf_link["text"])
                all_extracted_records.extend(pdf_records)
    elif run_pdf:
        logger.info("PDF extraction diaktifkan namun tidak ada dokumen PDF hasil yang terdeteksi.")

    # 5. Pengolahan & Penyimpanan Data (DataFrame & Export)
    if all_extracted_records:
        logger.info(f"[LANGKAH 4] Total terkumpul {len(all_extracted_records)} data skor atlet. Memproses ke Pandas...")
        df = IanseoDataHandler.create_dataframe(all_extracted_records)
        
        # Bersihkan nama file dari karakter aneh
        safe_event_name = "".join([c if c.isalnum() or c in (" ", "_", "-") else "" for c in event_name]).replace(" ", "_")
        export_paths = IanseoDataHandler.export_data(df, base_filename=f"ianseo_{event_id}_{safe_event_name}")
        
        logger.info("=" * 60)
        logger.info("PROSES SCRAPING BERHASIL SELESAI!")
        for fmt, path in export_paths.items():
            logger.info(f"[-] File {fmt.upper()}: {path}")
        logger.info("=" * 60)
    else:
        logger.error("=" * 60)
        logger.error("GAGAL: Tidak ada data atlet atau skor yang berhasil diekstraksi.")
        logger.error("=" * 60)


def show_demo_list():
    """Mendapatkan daftar turnamen Indonesia terbaru sebagai langkah awal (Level 1 Demo)."""
    print("\\n[DEMO LEVEL 1] Menampilkan Turnamen Indonesia Terkini di Ianseo:")
    print("-" * 75)
    engine = IanseoScraperEngine()
    events = engine.scrape_indonesian_events()
    
    if events:
        print(f"{'ID':<8} | {'Nama Turnamen':<35} | {'Tanggal':<15} | {'Lokasi'}")
        print("-" * 75)
        for ev in events[:10]: # Tampilkan 10 teratas
            print(f"{ev['event_id']:<8} | {ev['event_name'][:35]:<35} | {ev['date']:<15} | {ev['location']}")
    else:
        print("Gagal mengambil daftar turnamen.")
    print("-" * 75)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ianseo Archery Web Scraper Engine CLI - Indonesia Edition",
        epilog="Pastikan menggunakan engine ini secara bijak dan mematuhi etika scraping."
    )
    
    parser.add_argument("--event", type=str, help="ID Event Ianseo yang ingin di-scrape (contoh: 17290)")
    parser.add_argument("--demo", action="store_true", help="Jalankan demo mengambil daftar turnamen Indonesia (Level 1)")
    parser.add_argument("--pdf", action="store_true", help="Aktifkan ekstraksi hasil dari file PDF jika HTML tidak tersedia")
    parser.add_argument("--delay-min", type=float, default=1.5, help="Jeda minimal antar request (detik)")
    parser.add_argument("--delay-max", type=float, default=3.5, help="Jeda maksimal antar request (detik)")
    
    args = parser.parse_args()
    
    # Jika tidak ada argumen yang diberikan, tampilkan bantuan
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)
        
    if args.demo:
        show_demo_list()
    elif args.event:
        run_scraping_workflow(
            event_id=args.event, 
            delay_min=args.delay_min, 
            delay_max=args.delay_max, 
            run_pdf=args.pdf
        )
    else:
        parser.print_help()
`
  },
  {
    name: "README.md",
    language: "markdown",
    description: "Dokumentasi instalasi, konfigurasi, dan penggunaan lokal untuk tim Data Engineer.",
    content: `# Ianseo Archery Web Scraper Engine (Python)

Engine web scraper modular, robust, dan efisien yang dirancang khusus untuk mengekstrak data turnamen panahan, daftar kategori, dan detail skor atlet dari portal resmi **Ianseo (ianseo.net)**.

## Fitur Utama

- **Level 1 (Daftar Turnamen):** Ekstraksi otomatis turnamen skala nasional & daerah di Indonesia (\`TourList.php?countryid=INA\`).
- **Level 2 (Pemetaan Struktur Event):** Penelusuran dinamis menu kualifikasi, eliminasi, dan tautan PDF hasil di halaman \`Tournament.php\`.
- **Level 3 (Ekstraksi Skor & Atlet):** Parsing cerdas pada tabel skor HTML (\`ResultList.php\`) mencakup detail atlet, nomor target, klub/provinsi, skor per jarak, total skor, hingga jumlah tembakan 10s & Xs.
- **Ekstraksi PDF Opsional:** Integrasi engine \`pdfplumber\` untuk mengunduh, membaca, dan merapikan data atlet dari berkas PDF jika data tidak tersedia dalam tabel HTML.
- **Robustness & Scraping Etis:** 
  - Rotasi User-Agent otomatis dari daftar agen modern terpopuler.
  - Delay acak dinamis (*dynamic sleep*) untuk menghindari blokir IP (*anti-bot prevention*).
  - Penanganan error komprehensif (*HTTP errors*, *timeouts*, *missing HTML tags*).
- **Ekspor Data Terstruktur:** Output terintegrasi ke format **CSV**, **JSON**, dan **Excel Multi-Sheet** (per sheet per kategori) menggunakan Pandas.

---

## Persiapan Instalasi

1. **Clone atau Salin File Engine** ke folder lokal komputer Anda.
2. Pastikan Anda sudah menginstal **Python 3.8 ke atas**.
3. Buat virtual environment (direkomendasikan):
   \`\`\`bash
   python -m venv venv
   source venv/bin/activate  # Untuk Linux/macOS
   venv\\Scripts\\activate     # Untuk Windows
   \`\`\`
4. Instal semua library dependensi yang tertera di \`requirements.txt\`:
   \`\`\`bash
   pip install -r requirements.txt
   \`\`\`

---

## Petunjuk Penggunaan

### 1. Mengambil Daftar Turnamen Indonesia (Level 1)
Jalankan perintah ini untuk melakukan pencarian awal daftar turnamen yang terdaftar di Indonesia beserta ID Turnamennya:
\`\`\`bash
python main.py --demo
\`\`\`

### 2. Scraping Turnamen Spesifik Berdasarkan ID (Level 2 & 3)
Gunakan argumen \`--event\` diikuti dengan ID Turnamen Ianseo (misalnya: ID \`17290\`):
\`\`\`bash
python main.py --event 17290
\`\`\`

### 3. Mengaktifkan Parser PDF Otomatis
Jika turnamen target hanya memiliki hasil berbentuk PDF, tambahkan bendera \`--pdf\`:
\`\`\`bash
python main.py --event 17290 --pdf
\`\`\`

### 4. Mengonfigurasi Kecepatan Scraping (Delay)
Untuk menjaga beban server Ianseo tetap aman, Anda bisa mengatur jeda minimum dan maksimum antar request:
\`\`\`bash
python main.py --event 17290 --delay-min 2.0 --delay-max 5.0
\`\`\`

---

## Struktur Output Data

Hasil akhir akan disimpan di folder \`output_data/\` dengan nama berkas otomatis: \`ianseo_[ID]_[NAMA_TURNAMEN].[csv/xlsx/json]\`.

Format tabel hasil ekspor:
- **Rank**: Peringkat atlet di kategorinya.
- **BackNo**: Nomor punggung target.
- **Athlete Name**: Nama lengkap pemanah.
- **Club/Provinsi**: Klub asal, pengprov, atau perwakilan daerah.
- **Distance 1**: Skor tembakan sesi/jarak pertama.
- **Distance 2**: Skor tembakan sesi/jarak kedua.
- **Total Score**: Akumulasi nilai skor.
- **Tens**: Jumlah tembakan mengenai nilai 10.
- **Xs**: Jumlah tembakan tepat di lingkaran dalam X.
- **Category**: Divisi & kelas (misal: Recurve Men, Compound Master, Barebow Women).
- **Round**: Babak kompetisi (Kualifikasi / Eliminasi).

---

## Penanganan Masalah & Tantangan Teknis

1. **Error: "HTTP Error 403 Forbidden"**
   - *Penyebab*: IP Anda dicurigai atau diblokir sementara karena request terlalu cepat.
   - *Solusi*: Naikkan rentang delay menggunakan \`--delay-min 3.0 --delay-max 6.0\`.
2. **Kategori Custom / Karakter Non-ASCII**
   - Seluruh data string dikonversi dengan encoding \`utf-8\` untuk memastikan nama-nama atlet lokal atau klub dengan karakter khusus tetap terbaca dengan sempurna di sistem database Anda.
`
  }
];
