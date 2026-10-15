import re
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
        LEVEL 2: Memetakan menu link hasil dari halaman detail Ianseo.
        Ianseo menggunakan pattern /TourData/YYYY/ID/*.php untuk link hasil.
        - IQ*.php = Individual Qualification (Recurve/Compound/Barebow/Nacional)
        - TQ*.php = Team Qualification
        - E*.php  = Elimination / Bracket
        - EN*.php = Entry lists (participants)
        - ST*.php = Statistics
        """
        navigation_links = {
            "qualification_links": [],
            "elimination_links": [],
            "team_links": [],
            "pdf_documents": []
        }
        
        if not soup:
            return navigation_links

        all_links = soup.find_all("a", href=True)
        
        for link in all_links:
            href = link.get("href", "")
            text = link.get_text(strip=True)
            
            if not href or href == "#" or href.startswith("javascript"):
                continue
            
            # Convert relative URL to absolute
            if href.startswith("/"):
                full_url = f"https://www.ianseo.net{href}"
            elif not href.startswith("http"):
                full_url = f"https://www.ianseo.net/{href}"
            else:
                full_url = href
            
            # Skip non-TourData links (navigation, footer, etc.)
            if "TourData" not in full_url and "ResultList" not in full_url:
                continue
            
            # Cek apakah PDF - cek ini SEBELUM pattern matching
            if full_url.endswith(".pdf"):
                navigation_links["pdf_documents"].append(link_info)
                continue
            
            # Skip link dengan text kosong (biasanya icon PDF)
            if not text:
                continue
            
            link_info = {"text": text, "url": full_url}
            
            # Ekstrak nama file dari URL untuk klasifikasi
            filename = full_url.split("/")[-1].split("?")[0].upper()
            
            # Individual Qualification: IQ + type (R=Recurve, C=Compound, B=Barebow, N=Nacional)
            if filename.startswith("IQ"):
                navigation_links["qualification_links"].append(link_info)
            
            # Team Qualification: TQ + type
            elif filename.startswith("TQ"):
                navigation_links["team_links"].append(link_info)
            
            # Elimination/Bracket: E (but not EN which is entries)
            elif filename.startswith("E") and not filename.startswith("EN"):
                navigation_links["elimination_links"].append(link_info)
            
            # Fallback: ResultList.php pattern (old style)
            elif "ResultList.php" in href or "Result.php" in href:
                navigation_links["qualification_links"].append(link_info)
            
            elif "Team" in href or "ResultTeam" in href:
                navigation_links["team_links"].append(link_info)
            
            elif href.endswith(".pdf") or "Book.php" in href:
                navigation_links["pdf_documents"].append(link_info)
            
        logger.info(
            f"Selesai memetakan link detail. Hasil: "
            f"{len(navigation_links['qualification_links'])} Kualifikasi, "
            f"{len(navigation_links['elimination_links'])} Eliminasi, "
            f"{len(navigation_links['team_links'])} Team, "
            f"{len(navigation_links['pdf_documents'])} PDF"
        )
        return navigation_links

    @staticmethod
    def parse_category_info(category_name: str) -> Dict[str, str]:
        """
        Parse category name like 'NASIONAL U18 Women [After 72 Arrows]' into:
        - division: NASIONAL, RECURVE, COMPOUND, BAREBOW
        - class: U15, U18, U21, OPEN, etc.
        - gender: Men, Women, Mixed
        - arrows: 72, 36, 144, etc.
        """
        cat_upper = category_name.upper()
        
        # Division
        division = ""
        for div in ["NASIONAL", "RECURVE", "COMPOUND", "BAREBOW"]:
            if div in cat_upper:
                division = div
                break
        
        # Class
        class_val = ""
        class_patterns = [r"U(\d+)", r"U-?(\d+)", r"\bOPEN\b", r"\bSENIOR\b", r"\bJUNIOR\b", r"\bCADET\b"]
        if re.search(r"U\s?(\d+)", cat_upper):
            m = re.search(r"U\s?(\d+)", cat_upper)
            class_val = f"U{m.group(1)}"
        elif "OPEN" in cat_upper:
            class_val = "OPEN"
        elif "SENIOR" in cat_upper:
            class_val = "SENIOR"
        elif "JUNIOR" in cat_upper:
            class_val = "JUNIOR"
        elif "CADET" in cat_upper:
            class_val = "CADET"
        
        # Gender
        gender = ""
        if "WOMEN" in cat_upper or "WANITA" in cat_upper or " FEMALE" in cat_upper:
            gender = "Women"
        elif "MEN" in cat_upper or "PUTRA" in cat_upper or " MALE" in cat_upper:
            gender = "Men"
        elif "MIXED" in cat_upper or "CAMPURAN" in cat_upper:
            gender = "Mixed"
        
        # Arrows (from [After XX Arrows] or [XX Arrows])
        arrows = 0
        m = re.search(r"(\d+)\s*ARROWS?", cat_upper)
        if m:
            arrows = int(m.group(1))
        
        # Distance (extract from header like '50m-1', '40M-2')
        distance = ""
        m = re.search(r"(\d+)\s*M", category_name.upper())
        if m:
            distance = f"{m.group(1)}m"
        
        return {
            "division": division,
            "class": class_val,
            "gender": gender,
            "arrows": arrows,
            "distance": distance
        }

    @staticmethod
    def parse_scores_table(
        soup: BeautifulSoup, 
        category_name: str, 
        round_type: str = "Qualification",
        tournament_info: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """
        LEVEL 3: Ekstraksi Tabel Hasil Atlet & Skor.
        Menganalisis tabel skor Ianseo yang memiliki pola kolom berulang (Jarak 1, Jarak 2, dst).
        tournament_info: dict dengan keys year, date, location, organizer, event_name
        """
        records = []
        if not soup:
            return records
        
        tinfo = tournament_info or {}

        # Cari tabel data utama. Ianseo menggunakan class 'Griglia' untuk tabel data.
        # Jika tidak ada, cari tabel dengan baris terbanyak (skip tabel judul yang cuma 1 baris).
        table = (
            soup.find("table", {"class": "Griglia"}) or
            soup.find("table", {"class": "grid"}) or 
            soup.find("table", {"class": "display"}) or 
            soup.find("table", {"class": "tableVal"})
        )
        
        if not table:
            # Fallback: cari tabel dengan baris terbanyak
            all_tables = soup.find_all("table")
            if all_tables:
                table = max(all_tables, key=lambda t: len(t.find_all("tr")))
            
        if not table:
            logger.warning("Tabel hasil skor tidak ditemukan di halaman HTML.")
            return records

        rows = table.find_all("tr")
        if not rows:
            return records

        # Identifikasi header tabel untuk pemetaan kolom dinamis
        header_cols = []
        header_row = None
        
        # Helper: cek apakah th adalah header kolom (bukan category title)
        def is_column_header(th):
            colspan = int(th.get("colspan", 1))
            text = th.get_text(strip=True).lower()
            if colspan > 1:
                return False
            return text in ["rank", "pos.", "pos", "no", "athlete", "atlet", "name", "nama"]
        
        # Prioritas 1: Cari di <thead>
        thead = table.find("thead")
        if thead:
            th_tags = thead.find_all("th")
            if len(th_tags) > 1:
                # Cari th pertama yang merupakan header kolom (colspan=1, text singkat)
                first_data_idx = None
                for idx, th in enumerate(th_tags):
                    if is_column_header(th):
                        first_data_idx = idx
                        break
                if first_data_idx is not None:
                    header_row = thead
                    header_cols = [t.get_text(strip=True) for t in th_tags[first_data_idx:]]
        
        # Prioritas 2: Cari baris dengan <th> yang mengandung keyword header
        if not header_cols:
            for row in rows:
                th_tags = row.find_all("th")
                if not th_tags or len(th_tags) < 3:
                    continue
                # Cari th pertama yang merupakan header kolom (colspan=1, text singkat)
                first_data_idx = None
                for idx, th in enumerate(th_tags):
                    if is_column_header(th):
                        first_data_idx = idx
                        break
                if first_data_idx is not None:
                    header_row = row
                    header_cols = [t.get_text(strip=True) for t in th_tags[first_data_idx:]]
                    break
        
        # Expand header_cols berdasarkan colspan agar match dengan jumlah kolom data
        if header_cols and header_row:
            th_elements = header_row.find_all("th")
            # Jika header_cols mulai dari th ke-2 (th pertama dibuang karena category title),
            # offset index th_elements
            offset = len(th_elements) - len(header_cols)
            if offset < 0:
                offset = 0
            expanded = []
            for i, h in enumerate(header_cols):
                th_idx = i + offset
                if th_idx < len(th_elements):
                    colspan = int(th_elements[th_idx].get("colspan", 1))
                else:
                    colspan = 1
                expanded.extend([h] * colspan)
            header_cols = expanded
        
        # Jika tidak ditemukan header secara eksplisit, gunakan index default
        if not header_cols:
            logger.warning("Header tabel tidak terdeteksi secara otomatis. Menggunakan estimasi posisi kolom.")
            # Default header mapping untuk Ianseo
            header_cols = ["Rank", "BackNo", "Athlete", "Country", "Distance1", "Distance2", "Total", "10s", "Xs"]

        logger.info(f"Struktur header terdeteksi: {header_cols}")

        # Extract distance info from header (e.g. "50m-1" -> "50m")
        header_distance = ""
        for h in header_cols:
            m = re.search(r"(\d+)\s*[mM]", h)
            if m:
                header_distance = f"{m.group(1)}m"
                break

        # Mulai parsing baris data
        last_record = None  # Track record terakhir untuk merge detail row
        
        for row in rows:
            # Lewati baris header
            if row == header_row:
                continue
                
            cols = row.find_all("td")
            if not cols:
                continue
            
            # Deteksi detail row: td pertama colspan>=3 dan kosong, sisa td berisi skor
            # Struktur: [td colspan=3 empty] [td score1] [td score2] [td colspan=10 empty]
            first_colspan = int(cols[0].get("colspan", 1))
            first_text = cols[0].get_text(strip=True)
            if first_colspan >= 3 and not first_text and last_record:
                # Detail row: extract additional distances
                extra_dist_idx = 0
                for col in cols[1:]:
                    col_text = col.get_text(strip=True)
                    col_colspan = int(col.get("colspan", 1))
                    if col_text and col_colspan == 1:
                        # Find next available distance slot
                        for di in range(1, 11):
                            if last_record.get(f"distance_{di}", "0") == "0":
                                last_record[f"distance_{di}"] = col_text
                                break
                continue
            
            # Skip baris club name / distance breakdown (2 kolom)
            if len(cols) < 4:
                continue

            try:
                # Parse category info
                cat_info = IanseoParser.parse_category_info(category_name)
                
                atlet_info = {
                    "year": tinfo.get("year", ""),
                    "date_competition": tinfo.get("date", ""),
                    "location": tinfo.get("location", ""),
                    "organizer": tinfo.get("organizer", ""),
                    "event_name": tinfo.get("event_name", ""),
                    "division": cat_info["division"],
                    "class": cat_info["class"],
                    "gender": cat_info["gender"],
                    "rank": "",
                    "distance": header_distance or cat_info.get("distance", ""),
                    "athlete_name": "",
                    "club_provinsi": "",
                    "country": "",
                    "distance_1": "0",
                    "distance_2": "0",
                    "distance_3": "0",
                    "distance_4": "0",
                    "distance_5": "0",
                    "distance_6": "0",
                    "distance_7": "0",
                    "distance_8": "0",
                    "distance_9": "0",
                    "distance_10": "0",
                    "total_score": "0",
                    "tens": "0",
                    "xs": "0",
                    "arrows": cat_info["arrows"],
                    "index": "",
                    "category": category_name,
                    "round": round_type
                }

                # Metode 1: CSS class-based mapping (paling akurat untuk Ianseo)
                # TD classes: col Rank, col Athlete, col CoCode, col Country, col Dists, col Score, col Golds
                dist_values = []
                gold_values = []
                used_css_classes = False

                for col in cols:
                    css_classes = col.get("class", [])
                    css_str = " ".join(css_classes).lower()
                    col_text = col.get_text(strip=True)

                    if "rank" in css_str:
                        atlet_info["rank"] = col_text
                        used_css_classes = True
                    elif "athlete" in css_str:
                        atlet_info["athlete_name"] = col_text
                        used_css_classes = True
                    elif "country" in css_str and "cocode" not in css_str:
                        atlet_info["club_provinsi"] = col_text
                        atlet_info["country"] = col_text
                        used_css_classes = True
                    elif "dists" in css_str:
                        dist_values.append(col_text)
                        used_css_classes = True
                    elif "score" in css_str:
                        atlet_info["total_score"] = col_text
                        used_css_classes = True
                    elif "golds" in css_str:
                        gold_values.append(col_text)
                        used_css_classes = True

                # Assign distance values (pairs: score + rank for each distance)
                if dist_values:
                    scores = [dist_values[i] for i in range(0, len(dist_values), 2)]
                    for di, score in enumerate(scores):
                        if di < 10:
                            atlet_info[f"distance_{di+1}"] = score

                # Assign golds (10s and Xs)
                # Ianseo patterns:
                # 2018: Golds[0]=10+X (combined), Golds[1]=X
                # 2026: separate X and 10 columns (handled by header fallback)
                if gold_values:
                    if len(gold_values) >= 2:
                        # gold_values[0] = 10+X combined, gold_values[1] = X count
                        try:
                            ten_plus_x = int(gold_values[0])
                            xs_count = int(gold_values[1])
                            atlet_info["tens"] = str(ten_plus_x - xs_count)
                            atlet_info["xs"] = str(xs_count)
                        except ValueError:
                            atlet_info["tens"] = gold_values[0]
                            atlet_info["xs"] = gold_values[1]
                    else:
                        atlet_info["tens"] = gold_values[0]

                # Metode 2: Header-based mapping (fallback jika tidak ada CSS classes)
                if not used_css_classes:
                    row_data = [col.get_text(strip=True) for col in cols]
                    dist_count = 0
                    for idx, col_text in enumerate(row_data):
                        if idx >= len(header_cols):
                            break
                        header_name = header_cols[idx].lower()

                        if header_name in ["rank", "pos.", "no"]:
                            atlet_info["rank"] = col_text
                        elif header_name in ["athlete", "atlet", "name", "nama atlet", "nama"]:
                            atlet_info["athlete_name"] = col_text
                        elif "country" in header_name or "club" in header_name or "provinsi" in header_name or "prov" in header_name:
                            atlet_info["club_provinsi"] = col_text
                            atlet_info["country"] = col_text
                        elif "tot" in header_name or "total" in header_name or "score" in header_name:
                            atlet_info["total_score"] = col_text
                        elif header_name in ["10", "10s", "10's"] or "10+x" in header_name:
                            atlet_info["tens"] = col_text
                        elif header_name in ["x", "xs", "x's"]:
                            atlet_info["xs"] = col_text
                        elif "m-" in header_name or re.search(r"\d+m", header_name) or "distance" in header_name or "dist" in header_name:
                            if dist_count < 10:
                                atlet_info[f"distance_{dist_count+1}"] = col_text
                                dist_count += 1

                # Post-processing: Jika 10s dan Xs digabung di satu kolom (misal: "15 / 5")
                if "/" in atlet_info["tens"] and atlet_info["xs"] == "0":
                    parts = atlet_info["tens"].split("/")
                    atlet_info["tens"] = parts[0].strip()
                    atlet_info["xs"] = parts[1].strip() if len(parts) > 1 else "0"

                # Compute Index = total_score / arrows (3 decimal places)
                try:
                    total = int(atlet_info["total_score"])
                    arrows = int(atlet_info["arrows"])
                    
                    # Deteksi jumlah sesi/jarak yang terisi
                    valid_dists = [
                        int(str(atlet_info.get(f"distance_{i}", "0")).split("/")[0].strip() or 0)
                        for i in range(1, 11)
                        if str(atlet_info.get(f"distance_{i}", "0")).split("/")[0].strip().isdigit() and int(str(atlet_info.get(f"distance_{i}", "0")).split("/")[0].strip() or 0) > 0
                    ]
                    
                    # Estimasi akurat jumlah panah (arrows)
                    if len(valid_dists) >= 6:
                        arrows = 156
                    elif len(valid_dists) == 5:
                        arrows = 180
                    elif len(valid_dists) == 4:
                        arrows = 144
                    elif len(valid_dists) == 3:
                        arrows = 108
                    elif len(valid_dists) == 2 and (total > 360 or arrows < 72):
                        arrows = 72
                    elif total > 0 and (arrows == 0 or total / arrows > 10.0):
                        if total > 1080:
                            arrows = 144
                        elif total > 720:
                            arrows = 108
                        elif total > 360:
                            arrows = 72
                        else:
                            arrows = 36
                    
                    atlet_info["arrows"] = arrows
                    if arrows > 0 and total > 0:
                        calc_idx = min(10.0, total / arrows)
                        atlet_info["index"] = f"{calc_idx:.3f}"
                except (ValueError, ZeroDivisionError):
                    pass

                # Validasi minimal: Baris harus memiliki nama atlet
                if atlet_info["athlete_name"]:
                    records.append(atlet_info)
                    last_record = atlet_info
                    
            except Exception as e:
                logger.error(f"Error memparsing baris atlet: {e}")

        logger.info(f"Berhasil memparsing {len(records)} baris atlet dari tabel.")
        return records
