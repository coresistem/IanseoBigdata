#!/usr/bin/env python3
"""
CLI Batch Scraper for Ianseo Archery Data.
Runs independently from Streamlit — scraping continues in background.

Usage:
    python batch_scraper.py --year 2025
    python batch_scraper.py --year 2025 --all
    python batch_scraper.py --year 2025 --ids 12345,12346,12347
    python batch_scraper.py --year 2025 --search "jakarta" --all
    python batch_scraper.py --year 2025 --skip-scraped
"""
import argparse
import time
import logging
import sys
import os
import json
from scraper_engine import IanseoScraperEngine
from parser_engine import IanseoParser
from db_handler import ArcheryDatabase

STATUS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scraper_status.json")


def write_status(status, year=None, total=None, success=None, failed=None, records=None):
    """Write status to JSON file for Streamlit to read."""
    data = {
        "status": status,
        "pid": os.getpid(),
        "year": year,
        "total": total,
        "success": success,
        "failed": failed,
        "records": records,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    try:
        with open(STATUS_FILE, "w") as f:
            json.dump(data, f)
    except Exception:
        pass

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "batch_scraper.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)


def scrape_tournament(engine, db, tournament, year):
    """Scrape a single tournament and save to DB."""
    event_id = str(tournament.get("event_id", ""))
    event_name = tournament.get("event_name", "Unknown")

    try:
        detail_url = tournament.get("detail_url", f"https://www.ianseo.net/Details.php?toId={event_id}")
        detail_soup = engine.fetch_page(detail_url)

        if not detail_soup:
            logger.warning(f"[{event_id}] Gagal fetch detail page")
            return 0

        nav_links = IanseoParser.extract_event_navigation(detail_soup)
        qual_links = nav_links["qualification_links"]

        if not qual_links and not nav_links["elimination_links"] and not nav_links["team_links"]:
            tournament["year"] = str(year)
            db.save_tournament(tournament, 0, status="no_results")
            logger.warning(f"[{event_id}] {event_name} — no results published yet")
            return 0

        all_records = []
        for q_link in qual_links:
            cat_name = q_link["text"]
            url = q_link["url"]
            page_soup = engine.fetch_page(url)
            if page_soup:
                records = IanseoParser.parse_scores_table(
                    page_soup, category_name=cat_name, round_type="Qualification",
                    tournament_info={
                        "year": str(year),
                        "date": tournament.get("date", ""),
                        "location": tournament.get("location", ""),
                        "organizer": tournament.get("organizer", ""),
                        "event_name": event_name,
                    }
                )
                all_records.extend(records)
                logger.info(f"  [{event_id}] {cat_name[:40]}: {len(records)} records")

        if all_records:
            tournament["year"] = str(year)
            db.save_tournament(tournament, len(all_records))
            db.save_athletes(all_records, event_id)
            db.export_tournament_to_parquet(event_id)
            logger.info(f"[{event_id}] ✅ {event_name}: {len(all_records)} records saved")
            return len(all_records)
        else:
            tournament["year"] = str(year)
            db.save_tournament(tournament, 0, status="nodata")
            logger.warning(f"[{event_id}] {event_name}: no data extracted")
            return 0

    except Exception as e:
        logger.error(f"[{event_id}] ❌ {event_name}: {e}")
        return 0


def main():
    parser = argparse.ArgumentParser(description="Ianseo Archery Batch Scraper CLI")
    parser.add_argument("--year", required=True, type=int, help="Tahun turnamen (e.g. 2025)")
    parser.add_argument("--all", action="store_true", help="Scrape semua turnamen tahun tersebut")
    parser.add_argument("--ids", type=str, help="Comma-separated event IDs (e.g. 12345,12346)")
    parser.add_argument("--search", type=str, help="Filter by name/location")
    parser.add_argument("--skip-scraped", action="store_true", help="Skip turnamen yang sudah di-scrape")
    parser.add_argument("--delay-min", type=float, default=1.5, help="Min delay (seconds)")
    parser.add_argument("--delay-max", type=float, default=3.5, help="Max delay (seconds)")
    args = parser.parse_args()

    db = ArcheryDatabase()
    engine = IanseoScraperEngine(delay_range=(args.delay_min, args.delay_max))

    logger.info(f"=== Batch Scraper: Year {args.year} ===")

    # Fetch tournament list
    logger.info("Fetching tournament list...")
    tournaments = engine.scrape_indonesian_events(year=str(args.year), comptime="", time_type="local")
    logger.info(f"Found {len(tournaments)} tournaments")

    if not tournaments:
        logger.error("No tournaments found.")
        return

    # Filter by search
    if args.search:
        s = args.search.lower()
        tournaments = [t for t in tournaments if s in t.get("event_name", "").lower() or s in t.get("location", "").lower()]
        logger.info(f"After search filter '{args.search}': {len(tournaments)} tournaments")

    # Filter by IDs
    if args.ids:
        id_list = set(args.ids.split(","))
        tournaments = [t for t in tournaments if str(t.get("event_id", "")) in id_list]
        logger.info(f"After ID filter: {len(tournaments)} tournaments")

    # Skip already scraped (including nodata/no_results)
    if args.skip_scraped:
        scraped = db.get_scraped_event_ids()
        nodata = db.get_nodata_event_ids()
        skip_ids = scraped.union(nodata)
        before = len(tournaments)
        tournaments = [t for t in tournaments if str(t.get("event_id", "")) not in skip_ids]
        logger.info(f"Skipping {before - len(tournaments)} already-scraped or no-data tournaments")

    if not args.all and not args.ids:
        logger.info("\nTournaments found (use --all or --ids to scrape):")
        for t in tournaments:
            eid = t.get("event_id", "")
            name = t.get("event_name", "Unknown")
            date = t.get("date", "")
            loc = t.get("location", "")
            is_scraped = "✅" if str(eid) in db.get_scraped_event_ids() else "  "
            print(f"  {is_scraped} [{eid}] {date} | {loc[:20]:<20} | {name[:50]}")
        print(f"\nTotal: {len(tournaments)} tournaments")
        print(f"Use: python batch_scraper.py --year {args.year} --all")
        print(f"Or:  python batch_scraper.py --year {args.year} --ids <comma-separated-ids>")
        return

    # Scrape
    total = len(tournaments)
    write_status("running", year=args.year, total=total, success=0, failed=0, records=0)
    logger.info(f"\nStarting batch scraping: {total} tournaments")
    logger.info(f"Estimated time: {total * 0.5:.0f} - {total * 2:.0f} minutes")
    logger.info(f"Log file: batch_scraper.log")
    logger.info("=" * 60)

    start_time = time.time()
    success = 0
    total_records = 0
    failed = 0

    for idx, tournament in enumerate(tournaments):
        event_id = str(tournament.get("event_id", ""))
        event_name = tournament.get("event_name", "Unknown")

        logger.info(f"\n[{idx + 1}/{total}] {event_name[:60]}")

        records = scrape_tournament(engine, db, tournament, args.year)
        if records > 0:
            success += 1
            total_records += records
        else:
            failed += 1

        elapsed = time.time() - start_time
        remaining = (elapsed / (idx + 1)) * (total - idx - 1)
        write_status("running", year=args.year, total=total, success=success, failed=failed, records=total_records)
        logger.info(f"  Progress: {idx + 1}/{total} | Success: {success} | Failed: {failed} | "
                     f"Elapsed: {elapsed / 60:.1f}m | ETA: {remaining / 60:.1f}m")

    elapsed = time.time() - start_time
    logger.info("\n" + "=" * 60)
    logger.info(f"BATCH COMPLETE")
    logger.info(f"  Total tournaments: {total}")
    logger.info(f"  Success: {success}")
    logger.info(f"  Failed/No data: {failed}")
    logger.info(f"  Total records: {total_records}")
    logger.info(f"  Time: {elapsed / 60:.1f} minutes")
    logger.info(f"  Database: {db.db_path}")
    logger.info("=" * 60)
    write_status("completed", year=args.year, total=total, success=success, failed=failed, records=total_records)


if __name__ == "__main__":
    main()
