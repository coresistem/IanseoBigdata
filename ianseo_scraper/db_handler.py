"""
Database handler for Ianseo Archery Scraper.
Stack: Python + Streamlit + DuckDB + Parquet
DuckDB for query/analysis, Parquet for portable columnar storage.
"""
import duckdb
import pandas as pd
import logging
from pathlib import Path
from datetime import datetime
import threading

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "archery_bigdata.duckdb"
PARQUET_DIR = Path(__file__).parent / "parquet_data"


class ArcheryDatabase:
    """DuckDB-based storage for archery tournament data.
    Uses per-thread connections to avoid DuckDB threading issues."""

    def __init__(self, db_path: str = None, read_only: bool = False):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self.read_only = read_only
        self._init_db()

    def _get_conn(self):
        for attempt in range(5):
            try:
                return duckdb.connect(str(self.db_path))
            except duckdb.IOException:
                if attempt < 4:
                    import time
                    time.sleep(0.5)
                else:
                    raise

    def _init_db(self):
        try:
            conn = self._get_conn()
        except Exception as e:
            logger.warning(f"Could not init DB (will retry on next call): {e}")
            return
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tournaments (
                    event_id VARCHAR PRIMARY KEY,
                    event_code VARCHAR,
                    event_name VARCHAR,
                    year VARCHAR,
                    date VARCHAR,
                    location VARCHAR,
                    organizer VARCHAR,
                    detail_url VARCHAR,
                    scraped_at TIMESTAMP,
                    total_records INTEGER,
                    status VARCHAR DEFAULT 'success'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS athletes (
                    id INTEGER,
                    event_id VARCHAR,
                    year VARCHAR,
                    date_competition VARCHAR,
                    location VARCHAR,
                    organizer VARCHAR,
                    event_name VARCHAR,
                    division VARCHAR,
                    class VARCHAR,
                    gender VARCHAR,
                    rank INTEGER,
                    distance VARCHAR,
                    athlete_name VARCHAR,
                    club_provinsi VARCHAR,
                    country VARCHAR,
                    distance_1 INTEGER,
                    distance_2 INTEGER,
                    distance_3 INTEGER,
                    distance_4 INTEGER,
                    distance_5 INTEGER,
                    distance_6 INTEGER,
                    distance_7 INTEGER,
                    distance_8 INTEGER,
                    distance_9 INTEGER,
                    distance_10 INTEGER,
                    total_score INTEGER,
                    tens INTEGER,
                    xs INTEGER,
                    arrows INTEGER,
                    index_score DOUBLE,
                    category VARCHAR,
                    round VARCHAR
                )
            """)
            # Remove existing duplicates (keep first occurrence)
            conn.execute("""
                DELETE FROM athletes WHERE rowid NOT IN (
                    SELECT MIN(rowid) FROM athletes GROUP BY event_id, athlete_name, category, round
                )
            """)
            # Add unique constraint to prevent future duplicates
            try:
                conn.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_athlete_unique
                    ON athletes (event_id, athlete_name, category, round)
                """)
            except Exception:
                pass

            conn.execute("""
                CREATE TABLE IF NOT EXISTS athlete_aliases (
                    id INTEGER,
                    alias_name VARCHAR,
                    canonical_name VARCHAR,
                    records_count INTEGER,
                    merged_at TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE SEQUENCE IF NOT EXISTS athletes_id_seq
            """)
            
            conn.commit()
            logger.info(f"Database initialized at {self.db_path}")
        except Exception as e:
            logger.warning(f"DB init failed (likely read-only connection, tables should exist): {e}")
        finally:
            conn.close()

    def save_tournament(self, tournament: dict, total_records: int, status: str = "success"):
        """Insert or update tournament metadata."""
        conn = self._get_conn()
        try:
            event_id = str(tournament.get("event_id", ""))
            conn.execute(
                """
                INSERT OR REPLACE INTO tournaments
                (event_id, event_code, event_name, year, date, location, organizer, detail_url, scraped_at, total_records, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    event_id,
                    tournament.get("event_code", ""),
                    tournament.get("event_name", ""),
                    tournament.get("year", ""),
                    tournament.get("date", ""),
                    tournament.get("location", ""),
                    tournament.get("organizer", ""),
                    tournament.get("detail_url", ""),
                    datetime.now(),
                    total_records,
                    status,
                ],
            )
            conn.commit()
            logger.info(f"Saved tournament {event_id}: {total_records} records, status: {status}")
        finally:
            conn.close()

    def save_athletes(self, records: list, event_id: str):
        """Save athlete records to database. Replaces existing records for the same event."""
        conn = self._get_conn()
        try:
            # Delete existing records for this event
            conn.execute("DELETE FROM athletes WHERE event_id = ?", [str(event_id)])

            # Convert records to DataFrame for bulk insert
            df = pd.DataFrame(records)
            if df.empty:
                return

            # Ensure event_id column
            df["event_id"] = str(event_id)

            # Rename index to avoid conflict with DuckDB internal
            if "index" in df.columns:
                df = df.rename(columns={"index": "index_score"})

            # Select and order columns to match table schema
            columns = [
                "event_id", "year", "date_competition", "location", "organizer",
                "event_name", "division", "class", "gender", "rank", "distance",
                "athlete_name", "club_provinsi", "country",
                "distance_1", "distance_2", "distance_3", "distance_4",
                "distance_5", "distance_6", "distance_7", "distance_8",
                "distance_9", "distance_10",
                "total_score", "tens", "xs", "arrows", "index_score",
                "category", "round",
            ]
            for col in columns:
                if col not in df.columns:
                    df[col] = None

            # Clean distance values: "358/ 1" -> 358
            for col in [f"distance_{i}" for i in range(1, 11)]:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.split("/").str[0].str.strip()
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

            # Convert other numeric fields
            for col in ["rank", "total_score", "tens", "xs", "arrows"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
            if "index_score" in df.columns:
                df["index_score"] = pd.to_numeric(df["index_score"], errors="coerce").fillna(0.0)

            df = df[columns]

            # Register DataFrame and bulk insert
            conn.register("athletes_df", df)
            conn.execute("""
                INSERT OR REPLACE INTO athletes
                (event_id, year, date_competition, location, organizer, event_name,
                 division, class, gender, rank, distance, athlete_name, club_provinsi,
                 country, distance_1, distance_2, distance_3, distance_4, distance_5,
                 distance_6, distance_7, distance_8, distance_9, distance_10,
                 total_score, tens, xs, arrows, index_score, category, round)
                SELECT * FROM athletes_df
            """)
            conn.unregister("athletes_df")
            conn.commit()
            logger.info(f"Saved {len(records)} athlete records for event {event_id}")
        except Exception as e:
            logger.error(f"Error saving athletes: {e}")
            raise
        finally:
            conn.close()

    def is_tournament_scraped(self, event_id: str) -> bool:
        """Check if a tournament has already been scraped."""
        conn = self._get_conn()
        try:
            result = conn.execute(
                "SELECT COUNT(*) FROM tournaments WHERE event_id = ?",
                [str(event_id)],
            ).fetchone()
            return result[0] > 0
        finally:
            conn.close()

    def get_scraped_event_ids(self) -> set:
        """Get set of all scraped event IDs."""
        conn = self._get_conn()
        try:
            results = conn.execute("SELECT event_id FROM tournaments").fetchall()
            return {str(r[0]) for r in results}
        finally:
            conn.close()

    def get_nodata_event_ids(self) -> set:
        """Get set of event IDs with 'nodata' or 'no_results' status."""
        conn = self._get_conn()
        try:
            results = conn.execute("SELECT event_id FROM tournaments WHERE status IN ('nodata', 'no_results')").fetchall()
            return {str(r[0]) for r in results}
        except Exception:
            return set()
        finally:
            conn.close()

    def get_tournament_record_counts(self) -> dict:
        """Get event_id -> (saved_count, actual_count) mapping for crosscheck."""
        conn = self._get_conn()
        try:
            results = conn.execute("""
                SELECT t.event_id, t.total_records, COUNT(a.*) as actual
                FROM tournaments t
                LEFT JOIN athletes a ON t.event_id = a.event_id
                GROUP BY t.event_id, t.total_records
            """).fetchall()
            return {str(r[0]): {"saved": int(r[1]) if r[1] else 0, "actual": int(r[2])} for r in results}
        except Exception:
            return {}
        finally:
            conn.close()

    def get_all_tournaments(self) -> pd.DataFrame:
        """Get all scraped tournaments metadata."""
        conn = self._get_conn()
        try:
            return conn.execute("SELECT * FROM tournaments ORDER BY year DESC, event_name").df()
        finally:
            conn.close()

    # Column rename map for proper CSV headers
    ATHLETE_HEADERS = {
        "event_id": "Event ID", "year": "Year", "date_competition": "Date",
        "location": "Location", "organizer": "Organizer", "event_name": "Event Name",
        "division": "Division", "class": "Class", "gender": "Gender",
        "rank": "Rank", "distance": "Distance", "athlete_name": "Athlete Name",
        "club_provinsi": "Club/Provinsi", "country": "Country",
        "distance_1": "Dist 1", "distance_2": "Dist 2", "distance_3": "Dist 3",
        "distance_4": "Dist 4", "distance_5": "Dist 5", "distance_6": "Dist 6",
        "distance_7": "Dist 7", "distance_8": "Dist 8", "distance_9": "Dist 9",
        "distance_10": "Dist 10", "total_score": "Total Score", "tens": "10s",
        "xs": "Xs", "arrows": "Arrows", "index_score": "Index",
        "category": "Category", "round": "Round"
    }

    def get_all_athletes(self) -> pd.DataFrame:
        """Get all athlete records from all tournaments."""
        conn = self._get_conn()
        try:
            return conn.execute(
                "SELECT * FROM athletes ORDER BY year, event_name, division, distance, rank"
            ).df()
        finally:
            conn.close()

    def get_all_athletes_export(self) -> pd.DataFrame:
        """Get all athlete records with proper headers for CSV export."""
        df = self.get_all_athletes()
        if "id" in df.columns:
            df = df.drop(columns=["id"])
        return df.rename(columns=self.ATHLETE_HEADERS)

    def get_athletes_by_event(self, event_id: str) -> pd.DataFrame:
        """Get athlete records for a specific tournament."""
        conn = self._get_conn()
        try:
            return conn.execute(
                "SELECT * FROM athletes WHERE event_id = ?", [str(event_id)]
            ).df()
        finally:
            conn.close()

    def get_stats(self) -> dict:
        """Get database statistics."""
        conn = self._get_conn()
        try:
            tour_count = conn.execute("SELECT COUNT(*) FROM tournaments").fetchone()[0]
            athlete_count = conn.execute("SELECT COUNT(*) FROM athletes").fetchone()[0]
            years = conn.execute(
                "SELECT DISTINCT year FROM tournaments ORDER BY year"
            ).fetchall()
            return {
                "total_tournaments": tour_count,
                "total_athletes": athlete_count,
                "years": [r[0] for r in years],
            }
        finally:
            conn.close()

    def delete_tournament(self, event_id: str):
        """Delete a tournament and its athlete records."""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM athletes WHERE event_id = ?", [str(event_id)])
            conn.execute("DELETE FROM tournaments WHERE event_id = ?", [str(event_id)])
            conn.commit()
            logger.info(f"Deleted tournament {event_id}")
        finally:
            conn.close()

    def merge_athlete_names(self, canonical_name: str, alias_names: list) -> dict:
        """Merge multiple alias names into canonical_name in the athletes table.
        Safely resolves any conflicting unique index (event_id, athlete_name, category, round)
        by removing alias records if a canonical record already exists for that event/category/round.
        Logs the merge in athlete_aliases table."""
        canonical_name = str(canonical_name).strip()
        aliases = [str(a).strip() for a in alias_names if str(a).strip() and str(a).strip() != canonical_name]
        if not canonical_name or not aliases:
            return {"success": False, "updated_rows": 0, "error": "Nama acuan atau alias tidak valid."}

        conn = self._get_conn()
        try:
            conn.execute("BEGIN TRANSACTION")
            total_updated = 0

            for alias in aliases:
                cnt_row = conn.execute("SELECT COUNT(*) FROM athletes WHERE athlete_name = ?", [alias]).fetchone()
                cnt = cnt_row[0] if cnt_row else 0
                if cnt == 0:
                    continue

                # Remove alias record if canonical already exists in the same event/category/round to avoid duplicate key error
                conn.execute("""
                    DELETE FROM athletes 
                    WHERE athlete_name = ?
                      AND (event_id, category, round) IN (
                          SELECT event_id, category, round 
                          FROM athletes 
                          WHERE athlete_name = ?
                      )
                """, [alias, canonical_name])

                # Update alias records to canonical_name
                conn.execute("""
                    UPDATE athletes
                    SET athlete_name = ?
                    WHERE athlete_name = ?
                """, [canonical_name, alias])

                total_updated += cnt

                # Record into athlete_aliases log
                conn.execute("""
                    INSERT INTO athlete_aliases (alias_name, canonical_name, records_count, merged_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, [alias, canonical_name, cnt])

            conn.execute("COMMIT")
            logger.info(f"Merged aliases {aliases} into '{canonical_name}' ({total_updated} rows)")
            return {"success": True, "updated_rows": total_updated, "aliases": aliases}
        except Exception as e:
            try:
                conn.execute("ROLLBACK")
            except Exception:
                pass
            logger.error(f"Error merging athlete names: {e}")
            return {"success": False, "updated_rows": 0, "error": str(e)}
        finally:
            conn.close()

    def get_merge_history(self) -> list:
        """Get history of merged athlete names."""
        conn = self._get_conn()
        try:
            res = conn.execute("""
                SELECT alias_name, canonical_name, records_count, strftime(merged_at, '%Y-%m-%d %H:%M') as merged_time
                FROM athlete_aliases
                ORDER BY merged_at DESC
            """).fetchall()
            return [{"alias_name": r[0], "canonical_name": r[1], "records_count": r[2], "merged_at": r[3]} for r in res]
        except Exception:
            return []
        finally:
            conn.close()

    # ── Parquet integration ──────────────────────────────────────────

    def export_to_parquet(self) -> dict:
        """Export all DuckDB tables to Parquet files. Returns dict of file paths."""
        PARQUET_DIR.mkdir(exist_ok=True)
        conn = self._get_conn()
        paths = {}
        try:
            tournaments_path = str(PARQUET_DIR / "tournaments.parquet")
            athletes_path = str(PARQUET_DIR / "athletes.parquet")
            conn.execute(f"COPY tournaments TO '{tournaments_path}' (FORMAT PARquet)")
            conn.execute(f"COPY athletes TO '{athletes_path}' (FORMAT PARquet)")
            paths["tournaments"] = tournaments_path
            paths["athletes"] = athletes_path
            logger.info(f"Exported to Parquet: {paths}")
        finally:
            conn.close()
        return paths

    def export_tournament_to_parquet(self, event_id: str) -> str:
        """Export a single tournament's athletes to Parquet. Returns file path."""
        PARQUET_DIR.mkdir(exist_ok=True)
        conn = self._get_conn()
        try:
            path = str(PARQUET_DIR / f"athletes_{event_id}.parquet")
            conn.execute(
                f"COPY (SELECT * FROM athletes WHERE event_id = ?) TO '{path}' (FORMAT PARquet)",
                [str(event_id)],
            )
            logger.info(f"Exported tournament {event_id} to {path}")
            return path
        finally:
            conn.close()

    def import_from_parquet(self, tournaments_path: str = None, athletes_path: str = None):
        """Import data from Parquet files into DuckDB."""
        conn = self._get_conn()
        try:
            if tournaments_path:
                conn.execute(f"INSERT OR REPLACE INTO tournaments SELECT * FROM read_parquet('{tournaments_path}')")
            if athletes_path:
                conn.execute(f"INSERT INTO athletes SELECT * FROM read_parquet('{athletes_path}')")
            conn.commit()
            logger.info("Imported from Parquet")
        finally:
            conn.close()

    def get_parquet_info(self) -> dict:
        """Get info about Parquet files in the data directory."""
        if not PARQUET_DIR.exists():
            return {"exists": False, "files": []}
        files = []
        for f in PARQUET_DIR.glob("*.parquet"):
            files.append({
                "name": f.name,
                "size_mb": round(f.stat().st_size / 1024 / 1024, 2),
                "path": str(f),
            })
        return {"exists": True, "files": files}
