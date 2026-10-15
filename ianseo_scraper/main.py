# -*- coding: utf-8 -*-
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


def show_demo_list(year: str = None, comptime: str = None, time_type: str = None):
    """Mendapatkan daftar turnamen Indonesia terbaru sebagai langkah awal (Level 1 Demo)."""
    print("\\n[DEMO LEVEL 1] Menampilkan Turnamen Indonesia Terkini di Ianseo:")
    print("-" * 75)
    
    # Log parameter yang digunakan
    params_info = []
    if year:
        params_info.append(f"Year={year}")
    if comptime is not None:
        params_info.append(f"comptime={comptime}")
    if time_type:
        params_info.append(f"timeType={time_type}")
    
    if params_info:
        print(f"Parameter Filter: {', '.join(params_info)}")
        print("-" * 75)
    
    engine = IanseoScraperEngine()
    events = engine.scrape_indonesian_events(year=year, comptime=comptime, time_type=time_type)
    
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
    parser.add_argument("--year", type=str, help="Filter tahun turnamen (contoh: 2026)")
    parser.add_argument("--comptime", type=str, help="Filter waktu kompetisi (default: kosong)")
    parser.add_argument("--time-type", type=str, help="Tipe waktu (contoh: local)")
    
    args = parser.parse_args()
    
    # Jika tidak ada argumen yang diberikan, tampilkan bantuan
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)
        
    if args.demo:
        # Handle comptime - if not provided, use empty string
        comptime_val = args.comptime if args.comptime is not None else ""
        show_demo_list(year=args.year, comptime=comptime_val, time_type=args.time_type)
    elif args.event:
        run_scraping_workflow(
            event_id=args.event, 
            delay_min=args.delay_min, 
            delay_max=args.delay_max, 
            run_pdf=args.pdf
        )
    else:
        parser.print_help()
