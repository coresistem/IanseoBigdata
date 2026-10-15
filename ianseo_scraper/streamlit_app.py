import streamlit as st
import pandas as pd
import logging
import os
import threading
from scraper_engine import IanseoScraperEngine
from parser_engine import IanseoParser
from pdf_parser import IanseoPDFExtractor
from data_handler import IanseoDataHandler
from db_handler import ArcheryDatabase
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Cached fetch functions (available globally)
@st.cache_data(show_spinner=False)
def fetch_tournaments(year):
    engine = IanseoScraperEngine(delay_range=(0.5, 1.5))
    return engine.scrape_indonesian_events(year=year, comptime="", time_type="local")

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_participant_count(event_id):
    """Fetch participant count from ianseo for a single tournament."""
    engine = IanseoScraperEngine(delay_range=(0.5, 1.0))
    try:
        detail_url = f"https://www.ianseo.net/Details.php?toId={event_id}"
        soup = engine.fetch_page(detail_url)
        if not soup:
            return 0
        nav = IanseoParser.extract_event_navigation(soup)
        qual_links = nav.get("qualification_links", [])
        total = 0
        for q in qual_links:
            page = engine.fetch_page(q["url"])
            if page:
                tables = page.find_all("table")
                for t in tables:
                    rows = t.find_all("tr")
                    if len(rows) > 2:
                        cnt = sum(1 for r in rows if r.find("td") and not r.find("th"))
                        if cnt > 0:
                            total += cnt
                            break
        return total
    except Exception:
        return 0

# Shared state for background scraping threads
_scrape_lock = threading.Lock()

def get_scrape_status():
    if '_scrape_status' not in st.session_state:
        st.session_state['_scrape_status'] = {}
    return st.session_state['_scrape_status']

def _scrape_tournament_bg(event_id, tournament, year, delay_min, delay_max, scrape_status):
    """Background scrape function that runs in a separate thread.
    scrape_status is passed directly (dict reference) to avoid accessing st.session_state from thread."""
    with _scrape_lock:
        scrape_status[event_id] = {"status": "running", "count": 0, "error": "", "progress": 0, "total": 0, "current_cat": ""}
    try:
        engine = IanseoScraperEngine(delay_range=(delay_min, delay_max))
        detail_url = tournament.get('detail_url', f"https://www.ianseo.net/Details.php?toId={event_id}")
        detail_soup = engine.fetch_page(detail_url)
        
        if not detail_soup:
            with _scrape_lock:
                scrape_status[event_id] = {"status": "error", "count": 0, "error": "Gagal fetch detail page", "progress": 0, "total": 0, "current_cat": ""}
            return
        
        nav_links = IanseoParser.extract_event_navigation(detail_soup)
        qual_links = nav_links["qualification_links"]
        
        if not qual_links and not nav_links["elimination_links"] and not nav_links["team_links"]:
            tournament["year"] = year
            bg_db = ArcheryDatabase()
            bg_db.save_tournament(tournament, 0, status="no_results")
            with _scrape_lock:
                scrape_status[event_id] = {"status": "nodata", "count": 0, "error": "", "progress": 0, "total": 0, "current_cat": ""}
            return
        
        total_links = len(qual_links)
        all_records = []
        for i, q_link in enumerate(qual_links):
            cat_name = q_link["text"]
            with _scrape_lock:
                scrape_status[event_id] = {"status": "running", "count": len(all_records), "error": "", "progress": i, "total": total_links, "current_cat": cat_name}
            page_soup = engine.fetch_page(q_link["url"])
            if page_soup:
                records = IanseoParser.parse_scores_table(
                    page_soup, category_name=cat_name, round_type="Qualification",
                    tournament_info={
                        "year": year,
                        "date": tournament.get('date', ''),
                        "location": tournament.get('location', ''),
                        "organizer": tournament.get('organizer', ''),
                        "event_name": tournament.get('event_name', 'Unknown'),
                    }
                )
                all_records.extend(records)
        
        with _scrape_lock:
            scrape_status[event_id] = {"status": "running", "count": len(all_records), "error": "", "progress": total_links, "total": total_links, "current_cat": "Saving..."}
        
        if all_records:
            tournament["year"] = year
            bg_db = ArcheryDatabase()
            bg_db.save_tournament(tournament, len(all_records))
            bg_db.save_athletes(all_records, event_id)
            bg_db.export_tournament_to_parquet(event_id)
            with _scrape_lock:
                scrape_status[event_id] = {"status": "done", "count": len(all_records), "error": "", "progress": total_links, "total": total_links, "current_cat": ""}
        else:
            tournament["year"] = year
            bg_db = ArcheryDatabase()
            bg_db.save_tournament(tournament, 0, status="nodata")
            with _scrape_lock:
                scrape_status[event_id] = {"status": "nodata", "count": 0, "error": "", "progress": total_links, "total": total_links, "current_cat": ""}
    except Exception as e:
        with _scrape_lock:
            scrape_status[event_id] = {"status": "error", "count": 0, "error": str(e)[:100], "progress": 0, "total": 0, "current_cat": ""}

# Page configuration
st.set_page_config(
    page_title="Ianseo Archery Scraper",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stProgress > div > div > div > div {
        background-color: #10b981;
    }
    .metric-card {
        background-color: #1f2937;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #374151;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'current_step' not in st.session_state:
    st.session_state.current_step = 'year'
if 'view_mode' not in st.session_state:
    st.session_state.view_mode = 'scraper'
if 'selected_year' not in st.session_state:
    st.session_state.selected_year = ''
if 'selected_tournament' not in st.session_state:
    st.session_state.selected_tournament = None
if 'scraping_results' not in st.session_state:
    st.session_state.scraping_results = None
if 'selected_fields' not in st.session_state:
    st.session_state.selected_fields = {
        'year': True,
        'date_competition': True,
        'location': True,
        'organizer': True,
        'event_name': True,
        'division': True,
        'class': True,
        'gender': True,
        'rank': True,
        'distance': True,
        'athlete_name': True,
        'country': True,
        'distance_1': True,
        'distance_2': True,
        'distance_3': True,
        'distance_4': True,
        'distance_5': True,
        'distance_6': True,
        'distance_7': True,
        'distance_8': True,
        'distance_9': True,
        'distance_10': True,
        'arrows': True,
        'total_score': True,
        'index': True,
        'tens': True,
        'xs': True,
        'category': True,
    }

# Header
st.title("🎯 Ianseo Archery Scraper")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    
    view_mode = st.radio("Mode", ["🔧 Scraper", "📊 Big Data"], key="view_mode_radio")
    st.session_state.view_mode = 'bigdata' if 'Big Data' in view_mode else 'scraper'
    
    st.markdown("---")
    
    if st.session_state.view_mode == 'scraper':
        delay_min = st.slider("Min Delay (seconds)", 1.0, 5.0, 1.5, 0.1)
        delay_max = st.slider("Max Delay (seconds)", 2.0, 10.0, 3.5, 0.1)
        enable_pdf = st.checkbox("Enable PDF Extraction", value=False)
        
        st.markdown("---")
        st.markdown("### 📊 Progress")
        steps = ['year', 'tournaments', 'selection', 'batch_scraping', 'scraping', 'results']
        step_names = ['Pilih Tahun', 'Pilih Turnamen', 'Pilih Data', 'Batch Scraping', 'Scraping', 'Hasil']
        
        for i, (step, name) in enumerate(zip(steps, step_names)):
            if st.session_state.current_step == step:
                st.success(f"✓ {name}")
            elif steps.index(st.session_state.current_step) > i:
                st.success(f"✓ {name}")
            else:
                st.info(f"○ {name}")
        
        st.markdown("---")
        st.markdown("### 🚀 CLI Batch Scraper")
        st.markdown("Background scraping — tetap jalan meski pindah mode")
        
        # Read status from file (persists across mode switches)
        import json as _json
        status_file = os.path.join(os.path.dirname(__file__), "scraper_status.json")
        cli_status = None
        try:
            with open(status_file, "r") as f:
                cli_status = _json.load(f)
        except (FileNotFoundError, _json.JSONDecodeError):
            cli_status = None
        
        # Verify process is actually running if status says "running"
        cli_running = False
        if cli_status and cli_status.get("status") == "running":
            import psutil
            try:
                proc = psutil.Process(cli_status["pid"])
                if proc.is_running():
                    cli_running = True
            except (psutil.NoSuchProcess, psutil.AccessDenied, KeyError):
                cli_running = False
        
        if cli_running:
            st.success("🟢 CLI SEDANG BERJALAN")
            s = cli_status
            st.caption(f"PID: {s['pid']} | Tahun: {s.get('year')} | Update: {s.get('timestamp')}")
            
            done = s.get("success", 0) + s.get("failed", 0)
            total = s.get("total", 1)
            pct = int(done / total * 100) if total > 0 else 0
            
            st.progress(pct, text=f"Progress: {done}/{total} turnamen ({pct}%)")
            
            s_total = s.get("total", 0)
            s_success = s.get("success", 0)
            s_failed = s.get("failed", 0)
            s_records = s.get("records", 0)
            st.markdown(
                f"<div style='font-size:0.85rem;line-height:1.6'>"
                f"📊 Total: <b>{s_total}</b><br>"
                f"✅ Sukses: <b>{s_success}</b><br>"
                f"❌ Failed: <b>{s_failed}</b><br>"
                f"🎯 Records: <b>{s_records}</b>"
                f"</div>",
                unsafe_allow_html=True
            )
            
            col_stop, col_log, col_refresh = st.columns(3)
            with col_stop:
                if st.button("⏹️ Stop", key="stop_cli"):
                    try:
                        proc.terminate()
                        st.warning("Scraper dihentikan.")
                    except Exception:
                        st.error("Gagal menghentikan.")
            with col_log:
                if st.button("📄 Log", key="view_log"):
                    try:
                        with open("batch_scraper.log", "r", encoding="utf-8") as f:
                            log_content = f.read()
                            st.text_area("batch_scraper.log", log_content[-5000:], height=300)
                    except FileNotFoundError:
                        st.warning("Log file belum ada.")
            with col_refresh:
                if st.button("🔄 Refresh", key="refresh_cli"):
                    st.rerun()
            
            # Auto-refresh every 5 seconds
            time.sleep(5)
            st.rerun()
        elif cli_status and cli_status.get("status") == "completed":
            st.info(f"✅ Selesai! {cli_status.get('success', 0)}/{cli_status.get('total', 0)} | Records: {cli_status.get('records', 0)}")
            if st.button("🗑️ Clear Status"):
                os.remove(status_file)
                st.rerun()
            
            cli_year = st.selectbox("Tahun", list(range(2018, 2027)), index=7, key="cli_year")
            cli_all = st.checkbox("Scrape Semua", value=False, key="cli_all")
            cli_skip = st.checkbox("Skip Sudah Tersimpan", value=True, key="cli_skip")
            
            if st.button("🚀 Start CLI", type="primary", key="start_cli"):
                import subprocess
                cmd = ["venv\\Scripts\\python.exe", "batch_scraper.py", "--year", str(cli_year)]
                if cli_skip:
                    cmd.append("--skip-scraped")
                if cli_all:
                    cmd.append("--all")
                subprocess.Popen(cmd, cwd="d:\\Experiment\\M28-Ianseo-Data-Scaper\\ianseo_scraper")
                st.success("✅ CLI started!")
                st.rerun()
        else:
            cli_year = st.selectbox("Tahun", list(range(2018, 2027)), index=7, key="cli_year")
            cli_all = st.checkbox("Scrape Semua", value=False, key="cli_all")
            cli_skip = st.checkbox("Skip Sudah Tersimpan", value=True, key="cli_skip")
            
            if st.button("🚀 Start CLI", type="primary", key="start_cli"):
                import subprocess
                cmd = ["venv\\Scripts\\python.exe", "batch_scraper.py", "--year", str(cli_year)]
                if cli_skip:
                    cmd.append("--skip-scraped")
                if cli_all:
                    cmd.append("--all")
                subprocess.Popen(cmd, cwd="d:\\Experiment\\M28-Ianseo-Data-Scaper\\ianseo_scraper")
                st.success("✅ CLI started!")
                st.rerun()
        
        if st.button("🔄 Refresh Status"):
            st.rerun()
    else:
        db = ArcheryDatabase()
        stats = db.get_stats()
        st.metric("🏆 Tournaments", stats["total_tournaments"])
        st.metric("🎯 Athletes", stats["total_athletes"])
        if stats["years"]:
            st.markdown(f"**Years:** {', '.join(stats['years'])}")

@st.cache_data(ttl=300, show_spinner=False)
def load_cached_tournaments():
    db = ArcheryDatabase()
    return db.get_all_tournaments()

@st.cache_data(ttl=300, show_spinner=False)
def load_cached_athletes():
    db = ArcheryDatabase()
    return db.get_all_athletes()

# Main content
if st.session_state.view_mode == 'bigdata':
    st.header("📊 Big Data Archery Analysis")
    
    db = ArcheryDatabase()
    stats = db.get_stats()
    if stats["total_tournaments"] == 0:
        st.info("Belum ada data tersimpan. Gunakan mode **🔧 Scraper** untuk mengumpulkan data turnamen terlebih dahulu.")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🏆 Total Tournaments", stats["total_tournaments"])
        with col2:
            st.metric("🎯 Total Athletes", stats["total_athletes"])
        with col3:
            st.metric("📅 Years", ", ".join(stats["years"]))
        
        st.markdown("---")
        
        tab1, tab2, tab3, tab4 = st.tabs(["📋 All Tournaments", "🎯 All Athletes", "📈 Analytics", "📦 Parquet"])
        
        with tab1:
            df_tour = load_cached_tournaments()
            st.dataframe(df_tour, width="stretch")
            
            # Export
            st.markdown("### 💾 Export")
            csv_tour = df_tour.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Tournaments CSV", csv_tour, "archery_tournaments.csv", "text/csv")
        
        with tab2:
            df_ath_raw = load_cached_athletes()
            _header_map = {
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
            df_ath_export = df_ath_raw.drop(columns=["id"], errors="ignore").rename(columns=_header_map)
            st.dataframe(df_ath_export, width="stretch", height=500)
            
            st.markdown("### 💾 Export")
            exp_col1, exp_col2 = st.columns(2)
            with exp_col1:
                csv_ath = df_ath_export.to_csv(index=False, sep=";").encode('utf-8-sig')
                st.download_button("📥 Download CSV", csv_ath, "archery_all_athletes.csv", "text/csv")
            with exp_col2:
                if st.button("📊 Generate Excel Export (200k+ rows)"):
                    with st.spinner("Membuat file Excel (mungkin memakan waktu beberapa detik)..."):
                        import io
                        excel_buffer = io.BytesIO()
                        df_ath_export.to_excel(excel_buffer, index=False, engine="openpyxl")
                        st.download_button("📥 Download Excel", excel_buffer.getvalue(), "archery_all_athletes.xlsx",
                                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        
        with tab3:
            df_ath = load_cached_athletes()
            if not df_ath.empty:
                subtab_athlete, subtab_overall = st.tabs([
                    "🎯 Search by Name (Analisis Performa Atlet)",
                    "📊 Ringkasan & Peringkat Umum Turnamen"
                ])
                
                with subtab_athlete:
                    st.markdown("### 🏹 Analisis Performa Atlet ditiap Event")
                    st.caption("Cari atlet berdasarkan nama untuk menganalisa rekam jejak performa, progres akurasi per arrow (Index Score), peringkat, dan rincian skor ditiap event yang pernah diikuti.")
                    
                    # Search Input and optional Division filter
                    col_search, col_div_ath = st.columns([2, 1])
                    with col_search:
                        search_name = st.text_input(
                            "🔍 Ketik Nama Atlet:",
                            placeholder="Contoh: Diananda, Arif Dwi, Riau Ega, Putri...",
                            key="ath_search_input"
                        )
                        prefix_only = st.checkbox(
                            "Hanya Nama Depan (Awalan)",
                            value=False,
                            key="ath_prefix_only",
                            help="Hanya cari atlet yang namanya diawali dengan kata kunci ini (misal: 'Putri' hanya menampilkan atlet yang nama depannya Putri)."
                        )
                    with col_div_ath:
                        ath_div_options = ["Semua Divisi"] + sorted([str(d).strip() for d in df_ath["division"].dropna().unique() if str(d).strip()])
                        selected_div_filter = st.selectbox("Filter Divisi (Opsional):", ath_div_options, key="ath_div_filter")
                    
                    query = search_name.strip()
                    
                    if not query or len(query) < 2:
                        st.info("💡 **Petunjuk:** Ketik minimal 2 karakter pada kotak pencarian di atas untuk menemukan data atlet.")
                        
                        # Quick suggestions / popular athletes
                        st.markdown("**Contoh Atlet Populer (Klik untuk mengisi cepat):**")
                        quick_cols = st.columns(4)
                        quick_examples = ["Diananda", "Riau Ega", "Arif Dwi", "Alviyanto"]
                        for q_idx, q_name in enumerate(quick_examples):
                            with quick_cols[q_idx]:
                                if st.button(f"🎯 {q_name}", key=f"quick_btn_{q_name}"):
                                    st.session_state["ath_search_input"] = q_name
                                    st.rerun()
                    else:
                        # Find matching names with relevance sorting
                        import re
                        q_clean = query.strip()
                        q_lower = q_clean.lower()
                        matched_series = df_ath["athlete_name"].dropna().astype(str)
                        
                        if prefix_only:
                            matching_mask = matched_series.str.strip().str.contains(
                                rf"^(?:\d+[\.\s\-]+)?{re.escape(q_clean)}", case=False, regex=True, na=False
                            )
                        else:
                            matching_mask = matched_series.str.contains(q_clean, case=False, na=False)
                        
                        raw_matched = matched_series[matching_mask].unique().tolist()
                        
                        # Prioritaskan:
                        # 0: Nama yang diawali kata kunci (Nama Depan)
                        # 1: Kata utuh di tengah/belakang nama (\bquery\b)
                        # 2: Substring di dalam kata
                        def relevance_sort_key(name):
                            n_clean = re.sub(r"^\d+[\.\s\-]+", "", name.strip()).lower()
                            if n_clean.startswith(q_lower):
                                priority = 0
                            elif re.search(rf"\b{re.escape(q_lower)}\b", n_clean):
                                priority = 1
                            else:
                                priority = 2
                            return (priority, n_clean)
                        
                        matched_names = sorted(raw_matched, key=relevance_sort_key)
                        
                        if not matched_names:
                            st.warning(f"Tidak ditemukan atlet dengan kata kunci '{query}'. Silakan periksa kembali ejaan nama.")
                        else:
                            display_names = matched_names[:300]
                            if len(matched_names) > 300:
                                st.caption(f"Menampilkan 300 teratas (diprioritaskan nama depan) dari total {len(matched_names)} nama yang cocok.")
                            
                            # Helper untuk deteksi kemiripan nama atlet secara otomatis
                            import difflib
                            def get_similar_name_suggestions(primary_name, candidates, max_suggestions=10):
                                if not primary_name or not candidates:
                                    return [primary_name] if primary_name else []
                                primary_clean = re.sub(r"^\d+[\.\s\-]+", "", primary_name.strip()).lower()
                                p_tokens = set([w for w in re.split(r"[\s\.\(\)\-,/]+", primary_clean) if len(w) >= 2])
                                scored = []
                                for cand in candidates:
                                    if cand == primary_name:
                                        continue
                                    c_clean = re.sub(r"^\d+[\.\s\-]+", "", cand.strip()).lower()
                                    c_tokens = set([w for w in re.split(r"[\s\.\(\)\-,/]+", c_clean) if len(w) >= 2])
                                    overlap = p_tokens.intersection(c_tokens)
                                    ratio = difflib.SequenceMatcher(None, primary_clean, c_clean).ratio()
                                    if len(overlap) >= 2 or (len(p_tokens) <= 2 and len(overlap) >= 1 and ratio > 0.6) or ratio > 0.75:
                                        score = max(len(overlap) / max(len(p_tokens), 1), ratio)
                                        scored.append((cand, score))
                                scored.sort(key=lambda x: x[1], reverse=True)
                                return [primary_name] + [s[0] for s in scored[:max_suggestions]]
                            
                            # ── Mode Pemilihan & Merge Atlet ──
                            merge_mode = st.radio(
                                "Mode Analisis Atlet:",
                                [
                                    "👤 1 Nama Tunggal",
                                    "🔀 Merge Variasi Nama Tertentu (Pilih Sendiri)",
                                    "👥 Gabung Semua Hasil Pencarian"
                                ],
                                horizontal=True,
                                key="ath_merge_mode",
                                help="Pilih 'Merge Variasi Nama Tertentu' untuk menggabungkan event dari atlet yang sama ketika namanya tertulis berbeda di tiap turnamen."
                            )
                            
                            selected_athletes = []
                            primary_athlete_name = ""
                            
                            if merge_mode == "👤 1 Nama Tunggal":
                                selected_athlete_single = st.selectbox(
                                    f"Ditemukan {len(matched_names)} nama yang cocok. Pilih salah satu:",
                                    display_names,
                                    key="selected_athlete_dropdown"
                                )
                                selected_athletes = [selected_athlete_single]
                                primary_athlete_name = selected_athlete_single
                            
                            elif merge_mode == "🔀 Merge Variasi Nama Tertentu (Pilih Sendiri)":
                                if "extra_merge_dict" not in st.session_state:
                                    st.session_state["extra_merge_dict"] = {}

                                col_anchor, col_multi = st.columns([1, 2])
                                with col_anchor:
                                    anchor_athlete = st.selectbox(
                                        "1. Pilih Nama Acuan / Utama:",
                                        display_names,
                                        key="merge_anchor_dropdown",
                                        help="Pilih nama atlet utama. Sistem akan otomatis mendeteksi variasi nama yang mirip di sebelah kanan."
                                    )
                                    custom_name_toggle = st.checkbox(
                                        "✏️ Edit Nama Resmi (Kustom / Hapus Kata)",
                                        value=False,
                                        key=f"custom_name_toggle_{anchor_athlete}",
                                        help="Centang jika ingin mengubah/menghapus kata tertentu (seperti menghapus kata 'Sirkuit', nama klub, singkatan, dsb)."
                                    )
                                    if custom_name_toggle:
                                        custom_name_input = st.text_input(
                                            "Ketik nama resmi yang bersih:",
                                            value=anchor_athlete,
                                            key=f"custom_name_input_{anchor_athlete}"
                                        )
                                        primary_athlete_name = custom_name_input.strip() if custom_name_input.strip() else anchor_athlete
                                    else:
                                        primary_athlete_name = anchor_athlete
                                
                                current_extra = st.session_state["extra_merge_dict"].get(anchor_athlete, [])
                                auto_suggs = get_similar_name_suggestions(anchor_athlete, matched_names)
                                
                                # Gabungkan opsi dari hasil pencarian + julukan tambahan yang diinput bebas
                                merge_options = list(dict.fromkeys(matched_names + current_extra))
                                default_selection = list(dict.fromkeys(auto_suggs + current_extra))
                                
                                with col_multi:
                                    selected_athletes = st.multiselect(
                                        "2. Centang variasi penulisan / julukan nama yang ingin dimerge:",
                                        options=merge_options,
                                        default=default_selection,
                                        key=f"merge_athletes_multiselect_{anchor_athlete}",
                                        help="Pilih 2 atau lebih nama yang merupakan atlet yang sama untuk digabungkan seluruh skor dan riwayat eventnya."
                                    )
                                    if not selected_athletes:
                                        selected_athletes = [anchor_athlete]
                                
                                # ── Fitur Tambah Nama Julukan / Nickname dari Seluruh Database ──
                                with st.expander("➕ Tambah Nama Julukan / Nickname Lain (dari seluruh database)", expanded=bool(current_extra)):
                                    st.caption("Gunakan ini jika atlet memiliki nama julukan, alias, atau penulisan yang sama sekali berbeda dari kata kunci pencarian di atas.")
                                    col_nn1, _ = st.columns([3, 1])
                                    with col_nn1:
                                        nn_query = st.text_input(
                                            "Cari nama julukan / alias atlet di database:",
                                            placeholder="Ketik julukan (contoh: Jeje, Kancil, dll)...",
                                            key=f"nn_input_{anchor_athlete}"
                                        )
                                    if nn_query and len(nn_query.strip()) >= 2:
                                        all_unique_names = sorted(df_ath["athlete_name"].dropna().astype(str).unique().tolist())
                                        matched_nn = [n for n in all_unique_names if nn_query.strip().lower() in n.lower()]
                                        if matched_nn:
                                            col_pick, col_act = st.columns([3, 1])
                                            with col_pick:
                                                chosen_nn = st.selectbox(
                                                    f"Ditemukan {len(matched_nn)} nama di database yang cocok:",
                                                    matched_nn[:100],
                                                    key=f"chosen_nn_select_{anchor_athlete}"
                                                )
                                            with col_act:
                                                st.write("")
                                                st.write("")
                                                if st.button("➕ Tambahkan ke Merge", key=f"btn_add_nn_{anchor_athlete}"):
                                                    if anchor_athlete not in st.session_state["extra_merge_dict"]:
                                                        st.session_state["extra_merge_dict"][anchor_athlete] = []
                                                    if chosen_nn != anchor_athlete and chosen_nn not in st.session_state["extra_merge_dict"][anchor_athlete]:
                                                        st.session_state["extra_merge_dict"][anchor_athlete].append(chosen_nn)
                                                        st.success(f"'{chosen_nn}' berhasil ditambahkan ke daftar merge!")
                                                        st.rerun()
                                        else:
                                            st.warning(f"Tidak ditemukan atlet dengan kata '{nn_query}' di seluruh database.")
                                    
                                    if current_extra:
                                        st.markdown("**Julukan/Alias tambahan yang sudah ditambahkan:**")
                                        for ex in list(current_extra):
                                            c_tag1, c_tag2 = st.columns([4, 1])
                                            c_tag1.write(f"- 🏷️ `{ex}`")
                                            if c_tag2.button("🗑️ Hapus", key=f"del_ex_{anchor_athlete}_{ex}"):
                                                st.session_state["extra_merge_dict"][anchor_athlete].remove(ex)
                                                st.rerun()

                                if len(selected_athletes) > 1 or primary_athlete_name != anchor_athlete:
                                    st.success(f"🔗 **Merge Sementara Aktif:** Menggabungkan data dari {len(selected_athletes)} variasi penulisan nama ke profil **{primary_athlete_name}**.")
                                    
                                    # Opsi Simpan Merge Permanen ke Database
                                    alias_to_merge = [a for a in selected_athletes if a != primary_athlete_name]
                                    if alias_to_merge:
                                        with st.expander("💾 Simpan Hasil Merge ke Database Secara Permanen", expanded=False):
                                            st.markdown(
                                                f"Nama-nama berikut akan **diubah permanen** di database menjadi **`{primary_athlete_name}`**:"
                                            )
                                            for a in alias_to_merge:
                                                c = len(df_ath[df_ath["athlete_name"] == a])
                                                st.write(f"- `{a}` ({c} data event/ronde)")
                                            
                                            st.warning("⚠️ Perhatian: Aksi ini akan mengupdate tabel `athletes` di database secara permanen.")
                                            if st.button("🚀 Konfirmasi & Update Database Sekarang", type="primary", key="btn_confirm_merge_db"):
                                                with st.spinner("Mengupdate database..."):
                                                    db = ArcheryDatabase()
                                                    res = db.merge_athlete_names(primary_athlete_name, alias_to_merge)
                                                    if res["success"]:
                                                        if anchor_athlete in st.session_state.get("extra_merge_dict", {}):
                                                            st.session_state["extra_merge_dict"][anchor_athlete] = []
                                                        st.cache_data.clear()
                                                        st.success(f"✅ Berhasil! Sebanyak {res['updated_rows']} baris data telah diperbarui menjadi '{primary_athlete_name}'.")
                                                        time.sleep(1.2)
                                                        st.rerun()
                                                    else:
                                                        st.error(f"❌ Gagal update database: {res.get('error', 'Unknown error')}")
                                
                                # Riwayat Merge Atlet di Database
                                db_history = ArcheryDatabase().get_merge_history()
                                if db_history:
                                    with st.expander(f"📜 Riwayat Merge Atlet di Database ({len(db_history)} data)"):
                                        df_hist = pd.DataFrame(db_history)
                                        df_hist.columns = ["Nama Asal (Alias)", "Nama Resmi (Tujuan)", "Jumlah Record", "Waktu Merge"]
                                        st.dataframe(df_hist, use_container_width=True, hide_index=True)
                                        
                                        # Batalkan Merge jika salah
                                        st.markdown("##### ↩️ Batalkan Salah Satu Merge (Revert):")
                                        col_un1, col_un2 = st.columns([3, 1])
                                        with col_un1:
                                            unmerge_options = [f"{h['alias_name']} ➔ {h['canonical_name']} ({h['records_count']} data)" for h in db_history]
                                            selected_unmerge_str = st.selectbox("Pilih riwayat yang ingin dibatalkan:", unmerge_options, key="unmerge_item_select")
                                            selected_idx = unmerge_options.index(selected_unmerge_str)
                                            target_unmerge = db_history[selected_idx]
                                        with col_un2:
                                            st.write("")
                                            st.write("")
                                            if st.button("↩️ Batalkan Merge Ini", type="secondary", key="btn_execute_unmerge"):
                                                with st.spinner("Membatalkan merge..."):
                                                    db = ArcheryDatabase()
                                                    unres = db.unmerge_athlete(target_unmerge["alias_name"], target_unmerge["canonical_name"])
                                                    if unres["success"]:
                                                        st.cache_data.clear()
                                                        st.success(f"✅ Berhasil! Nama '{target_unmerge['canonical_name']}' dikembalikan menjadi '{target_unmerge['alias_name']}'.")
                                                        time.sleep(1.2)
                                                        st.rerun()
                                                    else:
                                                        st.error(f"❌ Gagal membatalkan: {unres.get('error')}")
                            
                            else:  # "👥 Gabung Semua Hasil Pencarian"
                                if len(matched_names) > 50:
                                    st.warning(f"⚠️ Perhatian: Ada {len(matched_names)} nama yang cocok dengan kata kunci '{query}'. Menggabungkan semua nama ini mungkin akan mencampur atlet yang berbeda. Disarankan gunakan mode '🔀 Merge Variasi Nama Tertentu'.")
                                selected_athletes = matched_names
                                primary_athlete_name = f"Hasil Gabungan: {query.upper()}"
                            
                            selected_athlete = primary_athlete_name
                            
                            # Filter data
                            df_target = df_ath[df_ath["athlete_name"].isin(selected_athletes)].copy()
                            
                            if selected_div_filter != "Semua Divisi":
                                df_target = df_target[df_target["division"] == selected_div_filter]
                            
                            if df_target.empty:
                                st.warning("Tidak ada data event untuk atlet ini pada divisi yang dipilih.")
                            else:
                                # Data cleaning & calculations
                                df_target["total_score"] = pd.to_numeric(df_target["total_score"], errors="coerce").fillna(0).astype(int)
                                df_target["arrows"] = pd.to_numeric(df_target["arrows"], errors="coerce").fillna(0).astype(int)
                                df_target["rank_num"] = pd.to_numeric(df_target["rank"], errors="coerce")
                                df_target["tens"] = pd.to_numeric(df_target["tens"], errors="coerce").fillna(0).astype(int)
                                df_target["xs"] = pd.to_numeric(df_target["xs"], errors="coerce").fillna(0).astype(int)
                                
                                df_target["arrows_eff"] = df_target.apply(
                                    lambda r: max(r["arrows"], int((r["total_score"] + 9) // 10) if r["total_score"] > r["arrows"] * 10 else r["arrows"]),
                                    axis=1
                                )
                                df_target["arrows_eff"] = df_target["arrows_eff"].replace(0, pd.NA)
                                df_target["index_calc"] = (df_target["total_score"] / df_target["arrows_eff"]).fillna(0.0).clip(upper=10.0).round(3)
                                df_target["event_name_clean"] = df_target["event_name"].astype(str).str.replace("\n", " ").str.strip()
                                df_target["club_clean"] = df_target["club_provinsi"].astype(str).str.replace("\xa0", " ").str.strip()
                                df_target["year_sort"] = pd.to_numeric(df_target["year"], errors="coerce").fillna(0).astype(int)
                                
                                # Sort chronologically
                                df_target = df_target.sort_values(by=["year_sort", "date_competition"], ascending=[True, True])
                                
                                # Athlete Profile Header
                                st.markdown("---")
                                if len(selected_athletes) > 1:
                                    target_title = f"🏹 {primary_athlete_name} (🔗 Merged {len(selected_athletes)} Variasi Nama)"
                                else:
                                    target_title = f"🏹 {primary_athlete_name}"
                                st.subheader(target_title)
                                
                                if len(selected_athletes) > 1:
                                    with st.expander(f"📋 Rincian {len(selected_athletes)} Variasi Penulisan Nama yang Dimerge"):
                                        counts = df_target["athlete_name"].value_counts().reset_index()
                                        counts.columns = ["Variasi Nama di Event", "Jumlah Partisipasi Event"]
                                        st.dataframe(counts, use_container_width=True, hide_index=True)
                                
                                # Extract profile metadata
                                clubs_list = [c for c in df_target["club_clean"].dropna().unique() if str(c).strip() and str(c).strip() not in ["None", "nan"]]
                                divs_list = [d for d in df_target["division"].dropna().unique() if str(d).strip() and str(d).strip() not in ["None", "nan"]]
                                genders_list = [g for g in df_target["gender"].dropna().unique() if str(g).strip() and str(g).strip() not in ["None", "nan"]]
                                
                                meta_info = []
                                if clubs_list:
                                    meta_info.append(f"**Klub/Provinsi:** {', '.join(clubs_list[:5])}")
                                if divs_list:
                                    meta_info.append(f"**Divisi:** {', '.join(divs_list)}")
                                if genders_list:
                                    meta_info.append(f"**Gender:** {', '.join(genders_list)}")
                                if meta_info:
                                    st.markdown(" • ".join(meta_info))
                                
                                # ── Key Performance Metrics ──
                                valid_scores = df_target[df_target["total_score"] > 0]
                                valid_indices = df_target[df_target["index_calc"] > 0]["index_calc"]
                                
                                mcol1, mcol2, mcol3, mcol4, mcol5, mcol6 = st.columns(6)
                                with mcol1:
                                    st.metric("🏆 Total Event", f"{df_target['event_name_clean'].nunique():,}")
                                with mcol2:
                                    best_r = int(df_target['rank_num'].min()) if df_target['rank_num'].notna().any() else "-"
                                    st.metric("🥇 Rank Terbaik", f"#{best_r}" if best_r != "-" else "-")
                                with mcol3:
                                    avg_idx = valid_indices.mean() if not valid_indices.empty else 0.0
                                    st.metric("🎯 Avg Index", f"{avg_idx:.3f} / 10.0")
                                with mcol4:
                                    max_idx = valid_indices.max() if not valid_indices.empty else 0.0
                                    st.metric("📈 Peak Index", f"{max_idx:.3f}")
                                with mcol5:
                                    max_pts = valid_scores["total_score"].max() if not valid_scores.empty else 0
                                    st.metric("🏹 High Score", f"{max_pts:,} pts")
                                with mcol6:
                                    total_10s = int(df_target["tens"].sum())
                                    total_xs = int(df_target["xs"].sum())
                                    st.metric("🎯 10s & Xs", f"{total_10s} / {total_xs}")
                                
                                # ── Performance Trend Chart ──
                                st.markdown("#### 📈 Tren Perkembangan Performa")
                                
                                # Make unique event label for timeline
                                def _make_event_label(row, idx):
                                    yr = str(row['year']).strip() if pd.notna(row['year']) and str(row['year']).strip() else 'N/A'
                                    ev = str(row['event_name_clean'])[:26]
                                    cat = f" [{row['division']}]" if pd.notna(row['division']) and str(row['division']).strip() else ""
                                    return f"{idx+1}. {yr} - {ev}{cat}"
                                
                                df_target_reset = df_target.reset_index(drop=True)
                                df_target_reset["Event_Timeline"] = [
                                    _make_event_label(row, i) for i, row in df_target_reset.iterrows()
                                ]
                                
                                chart_opt = st.radio(
                                    "Pilih Metrik Grafik:",
                                    ["🎯 Akurasi per Arrow (Index Score)", "🏆 Total Skor per Event"],
                                    horizontal=True,
                                    key="ath_chart_metric"
                                )
                                
                                if "Index Score" in chart_opt:
                                    chart_data = df_target_reset.set_index("Event_Timeline")[["index_calc"]].rename(
                                        columns={"index_calc": "Index Score (per Arrow)"}
                                    )
                                    st.line_chart(chart_data)
                                    st.caption("ℹ️ *Index Score dihitung dari Total Skor ÷ Total Arrows (skala 0.0 - 10.000). Nilai ini menstandarkan performa lintas turnamen dengan jumlah panah berbeda.*")
                                else:
                                    chart_data = df_target_reset.set_index("Event_Timeline")[["total_score"]].rename(
                                        columns={"total_score": "Total Score"}
                                    )
                                    st.bar_chart(chart_data)
                                
                                # ── Event-by-Event Performance Table ──
                                st.markdown("#### 📋 Riwayat Performa di Setiap Event")
                                
                                display_cols = [
                                    "year", "date_competition", "event_name_clean", "division",
                                    "category", "round", "distance", "rank", "total_score",
                                    "arrows_eff", "index_calc", "tens", "xs", "club_clean", "location"
                                ]
                                rename_cols = {
                                    "year": "Tahun",
                                    "date_competition": "Tanggal",
                                    "event_name_clean": "Nama Event",
                                    "division": "Divisi",
                                    "category": "Kategori",
                                    "round": "Round",
                                    "distance": "Jarak",
                                    "rank": "Rank",
                                    "total_score": "Total Skor",
                                    "arrows_eff": "Arrows",
                                    "index_calc": "Index Score",
                                    "tens": "10s",
                                    "xs": "Xs",
                                    "club_clean": "Klub / Provinsi",
                                    "location": "Lokasi"
                                }
                                
                                df_display = df_target[display_cols].rename(columns=rename_cols).copy()
                                st.dataframe(df_display, width="stretch", height=350)
                                
                                # ── Distance Breakdown Expander ──
                                with st.expander("🔍 Rincian Skor Tiap Seri / Jarak (Distance 1 - 10)"):
                                    dist_cols = [f"distance_{i}" for i in range(1, 11) if f"distance_{i}" in df_target.columns]
                                    active_dist_cols = [c for c in dist_cols if pd.to_numeric(df_target[c], errors="coerce").fillna(0).sum() > 0]
                                    if active_dist_cols:
                                        dist_table_cols = ["year", "event_name_clean", "round", "total_score"] + active_dist_cols
                                        dist_rename = {"year": "Tahun", "event_name_clean": "Nama Event", "round": "Round", "total_score": "Total"}
                                        for c in active_dist_cols:
                                            dist_rename[c] = c.replace("distance_", "Dist ")
                                        st.dataframe(df_target[dist_table_cols].rename(columns=dist_rename), width="stretch")
                                    else:
                                        st.info("Tidak ada rincian skor per jarak individual untuk event yang diikuti atlet ini.")
                                
                                # ── Export Athlete Data ──
                                st.markdown("#### 💾 Export Data Atlet")
                                athlete_slug = selected_athlete.replace(" ", "_").replace("/", "_")
                                csv_ath_data = df_display.to_csv(index=False, sep=";").encode("utf-8-sig")
                                st.download_button(
                                    f"📥 Download Riwayat Performa {selected_athlete} (CSV)",
                                    csv_ath_data,
                                    f"performa_{athlete_slug}.csv",
                                    "text/csv",
                                    key=f"dl_csv_{selected_athlete}"
                                )
                
                with subtab_overall:
                    # Filters at top
                    st.markdown("### 🔍 Filters")
                    col_div, col_dist = st.columns(2)
                    with col_div:
                        divisions = [d for d in df_ath["division"].dropna().unique().tolist() if str(d).strip()]
                        selected_division = st.selectbox("Division", ["All"] + sorted(divisions), key="filter_division")
                    with col_dist:
                        distances = [d for d in df_ath["distance"].dropna().unique().tolist() if str(d).strip()]
                        selected_distance = st.selectbox("Distance", ["All"] + sorted(distances), key="filter_distance")
                    
                    # Apply filters
                    df_filtered = df_ath.copy()
                    if selected_division != "All":
                        df_filtered = df_filtered[df_filtered["division"] == selected_division]
                    if selected_distance != "All":
                        df_filtered = df_filtered[df_filtered["distance"] == selected_distance]
                    
                    st.markdown(f"**Filtered Records:** `{len(df_filtered):,}`")
                    st.markdown("---")
                    
                    if df_filtered.empty:
                        st.warning("No data matches the selected filters.")
                    else:
                        # Clean & prepare numeric fields
                        df_filtered["total_score"] = pd.to_numeric(df_filtered["total_score"], errors="coerce").fillna(0).astype(int)
                        df_filtered["arrows"] = pd.to_numeric(df_filtered["arrows"], errors="coerce").fillna(0).astype(int)
                        
                        # Auto-correct arrows dynamically if total_score > arrows * 10
                        df_filtered["arrows_eff"] = df_filtered.apply(
                            lambda r: max(r["arrows"], int((r["total_score"] + 9) // 10) if r["total_score"] > r["arrows"] * 10 else r["arrows"]),
                            axis=1
                        )
                        df_filtered["arrows_eff"] = df_filtered["arrows_eff"].replace(0, pd.NA)
                        df_filtered["index_calc"] = (df_filtered["total_score"] / df_filtered["arrows_eff"]).fillna(0.0).clip(upper=10.0).round(3)
                        
                        # Filter out rows with 0 score for meaningful analytics
                        df_valid = df_filtered[df_filtered["total_score"] > 0].copy()
                        
                        if df_valid.empty:
                            st.warning("Semua data yang difilter memiliki skor 0.")
                        else:
                            # ── 1. Average Score by Year ──
                            st.markdown("### 📊 Average Score by Year")
                            avg_by_year = df_valid.groupby("year").agg(
                                Avg_Score=("total_score", "mean"),
                                Avg_Index=("index_calc", "mean"),
                                Top_Score=("total_score", "max"),
                                Highest_Index=("index_calc", "max"),
                                Count=("total_score", "count"),
                                Events=("event_name", "nunique")
                            ).reset_index()
                            avg_by_year.columns = ["Year", "Avg Score", "Avg Index", "Top Score", "Highest Index", "Total Athletes", "Events"]
                            avg_by_year["Avg Score"] = avg_by_year["Avg Score"].round(2)
                            avg_by_year["Avg Index"] = avg_by_year["Avg Index"].round(3)
                            avg_by_year["Highest Index"] = avg_by_year["Highest Index"].round(3)
                            st.dataframe(avg_by_year, width="stretch")
                            
                            # ── 2. Index Score Summary Metrics ──
                            st.markdown("### 📈 Index Score Summary (Skor ÷ Total Arrow)")
                            idx_valid = df_valid[df_valid["index_calc"] > 0]["index_calc"]
                            if not idx_valid.empty:
                                icol1, icol2, icol3, icol4 = st.columns(4)
                                with icol1:
                                    st.metric("Avg Index", f"{idx_valid.mean():.3f} / 10.000")
                                with icol2:
                                    st.metric("Min Index", f"{idx_valid.min():.3f}")
                                with icol3:
                                    st.metric("Max Index", f"{idx_valid.max():.3f}")
                                with icol4:
                                    st.metric("Valid Records", f"{len(idx_valid):,}")
                            
                            # ── 3. Top 20 Athletes (Default: By Index) ──
                            st.markdown("### 🥇 Top 20 Athletes Ranking")
                            
                            col_sort, col_min_arr = st.columns(2)
                            with col_sort:
                                sort_mode = st.radio(
                                    "Urutkan Peringkat Berdasarkan:",
                                    ["🎯 Top by Index (Akurasi per Arrow)", "🏆 Top by Total Score"],
                                    index=0,
                                    horizontal=True,
                                    key="top_sort_mode"
                                )
                            with col_min_arr:
                                min_arrow_opt = st.selectbox(
                                    "Filter Format Jumlah Panah:",
                                    ["Semua Format", "Minimal 36 Arrows", "Minimal 72 Arrows (Standar Kualifikasi)", "Format 144+ Arrows"],
                                    index=1,
                                    key="top_min_arrow"
                                )
                            
                            # Apply arrow filter for ranking
                            df_rank_pool = df_valid.copy()
                            if min_arrow_opt == "Minimal 36 Arrows":
                                df_rank_pool = df_rank_pool[df_rank_pool["arrows_eff"] >= 36]
                            elif min_arrow_opt == "Minimal 72 Arrows (Standar Kualifikasi)":
                                df_rank_pool = df_rank_pool[df_rank_pool["arrows_eff"] >= 72]
                            elif min_arrow_opt == "Format 144+ Arrows":
                                df_rank_pool = df_rank_pool[df_rank_pool["arrows_eff"] >= 144]
                            
                            if df_rank_pool.empty:
                                st.info("Tidak ada data atlet yang sesuai dengan filter format panah.")
                            else:
                                if "Index" in sort_mode:
                                    top20 = df_rank_pool.sort_values(by=["index_calc", "total_score"], ascending=[False, False]).head(20).copy()
                                else:
                                    top20 = df_rank_pool.sort_values(by=["total_score", "index_calc"], ascending=[False, False]).head(20).copy()
                                
                                top20.insert(0, "Rank", [f"#{i+1}" for i in range(len(top20))])
                                
                                tcol1, tcol2, tcol3 = st.columns(3)
                                with tcol1:
                                    st.metric("Top Athlete Index", f"{top20['index_calc'].iloc[0]:.3f} / 10.0")
                                with tcol2:
                                    st.metric("Top Athlete Score", f"{int(top20['total_score'].iloc[0])} pts")
                                with tcol3:
                                    st.metric("Avg Top 20 Index", f"{top20['index_calc'].mean():.3f}")
                                
                                st.dataframe(
                                    top20[["Rank", "athlete_name", "event_name", "year", "division", "distance", "total_score", "arrows", "index_calc", "tens", "xs"]]
                                        .rename(columns={
                                            "athlete_name": "Athlete", "event_name": "Event", "year": "Year",
                                            "division": "Division", "distance": "Distance", "total_score": "Total Score",
                                            "arrows": "Arrows", "index_calc": "Index Score", "tens": "10s", "xs": "Xs"
                                        }),
                                    width="stretch"
                                )
                            
                            # ── 4. Top Events by Athlete Count (dengan Analisis Top 16 Atlet) ──
                            st.markdown("### 📋 Top Events by Athlete Count (Analisis Top 16 Atlet)")
                            st.caption("ℹ️ *Catatan: Nilai **Avg Top 16 Index** & **Avg Top 16 Score** dihitung secara proporsional dari Top 16 atlet terbaik per event (atau sejumlah total peserta jika peserta < 16) untuk mencerminkan level performa kompetisi secara objektif dan valid.*")
                            
                            # Group by event and take top 16 per event
                            df_event_sort = df_valid.sort_values(by=["event_name", "index_calc", "total_score"], ascending=[True, False, False])
                            df_top16_per_event = df_event_sort.groupby("event_name").head(16)
                            
                            event_top16_agg = df_top16_per_event.groupby("event_name").agg(
                                Sampled_Athletes=("index_calc", "count"),
                                Avg_Top16_Index=("index_calc", "mean"),
                                Avg_Top16_Score=("total_score", "mean"),
                                Highest_Index=("index_calc", "max"),
                                Top_Score=("total_score", "max")
                            ).reset_index()
                            
                            event_total_counts = df_valid.groupby("event_name").agg(
                                Total_Athletes=("athlete_name", "count"),
                                Year=("year", lambda x: str(x.iloc[0]) if len(x) > 0 else "")
                            ).reset_index()
                            
                            merged_events = pd.merge(event_total_counts, event_top16_agg, on="event_name")
                            merged_events = merged_events.sort_values("Total_Athletes", ascending=False).head(20)
                            merged_events["Avg_Top16_Index"] = merged_events["Avg_Top16_Index"].round(3)
                            merged_events["Avg_Top16_Score"] = merged_events["Avg_Top16_Score"].round(1)
                            merged_events["Highest_Index"] = merged_events["Highest_Index"].round(3)
                            
                            st.dataframe(
                                merged_events[[
                                    "event_name", "Year", "Total_Athletes", "Sampled_Athletes",
                                    "Avg_Top16_Index", "Avg_Top16_Score", "Highest_Index", "Top_Score"
                                ]].rename(columns={
                                    "event_name": "Event Name",
                                    "Total_Athletes": "Total Participants",
                                    "Sampled_Athletes": "Sampled (max 16)",
                                    "Avg_Top16_Index": "Avg Top 16 Index",
                                    "Avg_Top16_Score": "Avg Top 16 Score",
                                    "Highest_Index": "Highest Index",
                                    "Top_Score": "Top Score"
                                }),
                                width="stretch"
                            )
                            
                            # ── 5. Overall Statistics ──
                            st.markdown("### 📊 Overall Statistics")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Total Records", f"{len(df_valid):,}")
                            with col2:
                                st.metric("Unique Athletes", f"{df_valid['athlete_name'].nunique():,}")
                            with col3:
                                st.metric("Unique Events", f"{df_valid['event_name'].nunique():,}")
            else:
                st.info("No athlete data available for analytics.")
        
        with tab4:
            st.markdown("### 📦 Parquet Storage")
            st.markdown("Parquet adalah format columnar yang efisien untuk big data analysis. "
                        "DuckDB dapat membaca file Parquet langsung dengan kecepatan tinggi.")
            
            col_exp, col_imp = st.columns(2)
            
            with col_exp:
                st.markdown("#### Export Master Parquet")
                if st.button("📦 Export All to Parquet (Master Files)", type="primary"):
                    try:
                        with st.spinner("Mengexport seluruh data DuckDB ke Parquet..."):
                            paths = db.export_to_parquet()
                            st.success(f"✅ Berhasil export: `{paths['tournaments']}` & `{paths['athletes']}`")
                    except Exception as e:
                        st.error(f"Export failed: {e}")
                
                # Show existing Parquet files in dataframe
                pq_info = db.get_parquet_info()
                if pq_info["exists"] and pq_info["files"]:
                    total_pq_size = sum(f["size_mb"] for f in pq_info["files"])
                    st.markdown(f"#### 📁 Existing Parquet Files ({len(pq_info['files'])} files, Total: {total_pq_size:.2f} MB)")
                    
                    df_pq = pd.DataFrame(pq_info["files"])
                    st.dataframe(
                        df_pq[["name", "size_mb"]].rename(columns={"name": "File Name", "size_mb": "Size (MB)"}),
                        width="stretch",
                        height=250
                    )
                    
                    # Single selectbox for downloading individual parquet file on demand
                    file_options = [f["name"] for f in pq_info["files"]]
                    selected_file_name = st.selectbox("Pilih file Parquet untuk diunduh:", file_options)
                    if selected_file_name:
                        selected_file = next((f for f in pq_info["files"] if f["name"] == selected_file_name), None)
                        if selected_file:
                            with open(selected_file["path"], "rb") as pf:
                                st.download_button(
                                    f"📥 Download {selected_file_name} ({selected_file['size_mb']} MB)",
                                    pf.read(),
                                    selected_file_name,
                                    "application/octet-stream",
                                    key=f"dl_{selected_file_name}"
                                )
            
            with col_imp:
                st.markdown("#### Import from Parquet")
                uploaded_tour = st.file_uploader("Upload tournaments.parquet", type=["parquet"], key="pq_tour")
                uploaded_ath = st.file_uploader("Upload athletes.parquet", type=["parquet"], key="pq_ath")
                
                if uploaded_tour or uploaded_ath:
                    if st.button("📥 Import Parquet to DuckDB", type="primary"):
                        try:
                            import tempfile
                            tour_path = None
                            ath_path = None
                            if uploaded_tour:
                                with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
                                    tmp.write(uploaded_tour.read())
                                    tour_path = tmp.name
                            if uploaded_ath:
                                with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
                                    tmp.write(uploaded_ath.read())
                                    ath_path = tmp.name
                            db = ArcheryDatabase()
                            db.import_from_parquet(tour_path, ath_path)
                            st.success("✅ Import berhasil! Refresh halaman untuk melihat data.")
                        except Exception as e:
                            st.error(f"Import failed: {e}")

elif st.session_state.current_step in ('year', 'tournaments'):
    # Initialize selected_year if not set
    if 'selected_year' not in st.session_state:
        st.session_state.selected_year = '2024'
    
    # ── Year selection (top section) ──
    st.header("📅 Pilih Tahun Turnamen")
    
    years = list(range(2018, 2027))
    cols = st.columns(4)
    
    # Pre-fetch DB stats once
    db = ArcheryDatabase()
    scraped_ids = db.get_scraped_event_ids()
    nodata_ids = db.get_nodata_event_ids()
    
    # Cache year stats in session_state to avoid refetch on every rerun
    if 'year_stats' not in st.session_state:
        st.session_state['year_stats'] = {}
    
    # Fetch tournament counts for all years (with spinner)
    needs_fetch = any(str(y) not in st.session_state['year_stats'] for y in years)
    if needs_fetch:
        with st.spinner("Mengambil statistik turnamen..."):
            for year in years:
                year_key = str(year)
                if year_key in st.session_state['year_stats']:
                    continue
                try:
                    tournaments = fetch_tournaments(year_key)
                    total_events = len(tournaments)
                    scraped_count = sum(1 for t in tournaments if str(t.get('event_id', '')) in scraped_ids)
                    empty_count = sum(1 for t in tournaments if str(t.get('event_id', '')) in nodata_ids)
                    unscraped_count = total_events - scraped_count - empty_count
                    st.session_state['year_stats'][year_key] = {
                        'total': total_events, 'scraped': scraped_count,
                        'empty': empty_count, 'unscraped': unscraped_count
                    }
                except Exception:
                    st.session_state['year_stats'][year_key] = None
    
    for i, year in enumerate(years):
        col = cols[i % 4]
        with col:
            year_key = str(year)
            stats = st.session_state['year_stats'].get(year_key)
            if stats:
                stats_text = f"{stats['total']} Event | {stats['scraped']} Terdata | {stats['empty']} Kosong | {stats['unscraped']} Unscrape"
            else:
                stats_text = "Gagal fetch"
            
            is_selected = st.session_state.selected_year == str(year)
            btn_type = "primary" if is_selected else "secondary"
            if st.button(f"**{year}**\n\n{stats_text}", key=f"year_{year}", use_container_width=True, type=btn_type):
                st.session_state.selected_year = str(year)
                st.session_state.current_step = 'tournaments'
                st.rerun()
    
    st.markdown("---")
    
    # ── Tournament list (bottom section) ──
    st.header(f"🏆 Daftar Turnamen {st.session_state.selected_year}")
    
    # Search filter
    search_query = st.text_input("🔍 Cari turnamen...", key="tournament_search", placeholder="Ketik nama turnamen atau lokasi")
    
    with st.spinner("Mengambil daftar turnamen dari ianseo.net..."):
        try:
            tournaments = fetch_tournaments(st.session_state.selected_year)
        except Exception as e:
            st.error(f"Gagal mengambil data: {str(e)}")
            tournaments = []
    
    if tournaments:
        # Get scraped event IDs and record counts
        db = ArcheryDatabase()
        scraped_ids = db.get_scraped_event_ids()
        nodata_ids = db.get_nodata_event_ids()
        record_counts = db.get_tournament_record_counts()
        
        # Filter berdasarkan search query
        if search_query:
            search_lower = search_query.lower()
            tournaments = [t for t in tournaments if search_lower in t.get('event_name', '').lower() or search_lower in t.get('location', '').lower()]
            st.info(f"Menampilkan {len(tournaments)} turnamen yang cocok dengan pencarian")
        
        # Sort: not scraped (top) > scraped with data (middle) > scraped 0 data/nodata (bottom)
        def sort_key(t):
            eid = str(t.get('event_id', ''))
            if eid not in scraped_ids:
                return (0, t.get('date', ''))  # Not scraped — top
            elif eid in nodata_ids or record_counts.get(eid, {}).get("actual", 0) == 0:
                return (2, t.get('date', ''))  # Scraped but 0 data/nodata — bottom
            else:
                return (1, t.get('date', ''))  # Scraped with data — middle
        
        tournaments.sort(key=sort_key)
        
        # Count for summary
        scrape_status = get_scrape_status()
        not_scraped = sum(1 for t in tournaments if str(t.get('event_id', '')) not in scraped_ids)
        has_data = sum(1 for t in tournaments if str(t.get('event_id', '')) in scraped_ids and str(t.get('event_id', '')) not in nodata_ids and record_counts.get(str(t.get('event_id', '')), {}).get("actual", 0) > 0)
        no_data = sum(1 for t in tournaments if str(t.get('event_id', '')) in nodata_ids or (str(t.get('event_id', '')) in scraped_ids and record_counts.get(str(t.get('event_id', '')), {}).get("actual", 0) == 0))
        
        st.success(f"Ditemukan **{len(tournaments)}** turnamen")
        
        # Filter buttons
        if 'status_filter' not in st.session_state:
            st.session_state['status_filter'] = 'all'
        
        fcol1, fcol2, fcol3, fcol4 = st.columns(4)
        with fcol1:
            f_all = st.button(f"📋 Semua: **{len(tournaments)}**", key="filter_all", use_container_width=True,
                              type="primary" if st.session_state['status_filter'] == 'all' else "secondary")
            if f_all:
                st.session_state['status_filter'] = 'all'
                st.rerun()
        with fcol2:
            f_unscrape = st.button(f"🔵 Belum scrape: **{not_scraped}**", key="filter_unscrape", use_container_width=True,
                                   type="primary" if st.session_state['status_filter'] == 'unscrape' else "secondary")
            if f_unscrape:
                st.session_state['status_filter'] = 'unscrape'
                st.rerun()
        with fcol3:
            f_data = st.button(f"✅ Ada data: **{has_data}**", key="filter_data", use_container_width=True,
                               type="primary" if st.session_state['status_filter'] == 'data' else "secondary")
            if f_data:
                st.session_state['status_filter'] = 'data'
                st.rerun()
        with fcol4:
            f_nodata = st.button(f"⚠️ Data kosong: **{no_data}**", key="filter_nodata", use_container_width=True,
                                 type="primary" if st.session_state['status_filter'] == 'nodata' else "secondary")
            if f_nodata:
                st.session_state['status_filter'] = 'nodata'
                st.rerun()
        
        # Apply status filter
        if st.session_state['status_filter'] == 'unscrape':
            tournaments = [t for t in tournaments if str(t.get('event_id', '')) not in scraped_ids]
        elif st.session_state['status_filter'] == 'data':
            tournaments = [t for t in tournaments if str(t.get('event_id', '')) in scraped_ids and str(t.get('event_id', '')) not in nodata_ids and record_counts.get(str(t.get('event_id', '')), {}).get("actual", 0) > 0]
        elif st.session_state['status_filter'] == 'nodata':
            tournaments = [t for t in tournaments if str(t.get('event_id', '')) in nodata_ids or (str(t.get('event_id', '')) in scraped_ids and record_counts.get(str(t.get('event_id', '')), {}).get("actual", 0) == 0)]
        
        # Batch scrape controls
        st.markdown("### 🚀 Batch Scraping")
        col_batch1, col_batch2, col_batch3 = st.columns([2, 1, 1])
        with col_batch1:
            batch_mode = st.checkbox("Aktifkan multi-select untuk batch scraping")
        with col_batch2:
            if batch_mode:
                if st.button("📋 Pilih Semua", key="select_all"):
                    for t in tournaments:
                        st.session_state[f"batch_{t.get('event_id')}"] = True
                    st.rerun()
        with col_batch3:
            if batch_mode:
                if st.button("🗑️ Clear Semua", key="clear_all"):
                    for t in tournaments:
                        st.session_state[f"batch_{t.get('event_id')}"] = False
                    st.rerun()
        
        if batch_mode:
            selected_count = sum(1 for t in tournaments if st.session_state.get(f"batch_{t.get('event_id')}", False))
            if selected_count > 0:
                st.info(f"**{selected_count}** turnamen dipilih untuk batch scraping")
                if st.button(f"🚀 Scrape {selected_count} Turnamen", type="primary", use_container_width=True):
                    st.session_state.batch_tournaments = [
                        t for t in tournaments if st.session_state.get(f"batch_{t.get('event_id')}", False)
                    ]
                    st.session_state.current_step = 'batch_scraping'
                    st.rerun()
        
        for tournament in tournaments:
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                event_id = str(tournament.get('event_id', ''))
                is_scraped = event_id in scraped_ids
                is_nodata = event_id in nodata_ids
                with col1:
                    event_code = tournament.get('event_code', '')
                    event_name = tournament.get('event_name', 'Unknown')
                    detail_url = tournament.get('detail_url', f"https://www.ianseo.net/Details.php?toId={event_id}")
                    rc = record_counts.get(event_id, {"saved": 0, "actual": 0})
                    saved = rc.get("saved", 0)
                    actual = rc.get("actual", 0)
                    if is_nodata:
                        badge = " ⚠️ No data"
                        tick = "⚠️ "
                    elif is_scraped and actual == 0:
                        badge = " ⚠️ (0 data)"
                        tick = "⚠️ "
                    elif is_scraped:
                        badge = f" ✅ ({actual} atlet)"
                        tick = "✅ "
                    else:
                        scrape_status = get_scrape_status()
                        with _scrape_lock:
                            _bg = scrape_status.get(event_id, {})
                        if _bg.get("status") == "nodata":
                            badge = " ⚠️ Data kosong"
                            tick = "⚠️ "
                        else:
                            badge = ""
                            tick = "🔵 "
                    st.markdown(f"**{tick}[{event_name}]({detail_url})**{badge}", unsafe_allow_html=True)
                    if event_code:
                        if is_scraped:
                            st.caption(f"Code: {event_code} | 🎯 {saved} peserta | 📦 {actual} data")
                        else:
                            # Lazy fetch button for unscraped tournaments
                            cek_key = f"cek_{event_id}"
                            if st.button(f"🔍 Cek Peserta", key=cek_key, help=f"Fetch jumlah peserta dari ianseo untuk {event_name}"):
                                cnt = fetch_participant_count(event_id)
                                st.session_state[f"ianseo_cnt_{event_id}"] = cnt
                                if cnt == 0:
                                    tournament["year"] = st.session_state.selected_year
                                    db = ArcheryDatabase()
                                    db.save_tournament(tournament, 0)
                                st.rerun()
                            cached_cnt = st.session_state.get(f"ianseo_cnt_{event_id}")
                            if cached_cnt is not None:
                                st.caption(f"Code: {event_code} | 🎯 {cached_cnt} peserta di ianseo")
                            else:
                                st.caption(f"Code: {event_code}")
                with col2:
                    st.markdown(f"📅 {tournament.get('date', 'N/A')}")
                with col3:
                    st.markdown(f"📍 {tournament.get('location', 'N/A')}")
                with col4:
                    if batch_mode:
                        st.checkbox("Pilih", key=f"batch_{event_id}", value=st.session_state.get(f"batch_{event_id}", False))
                    elif is_scraped:
                        if st.button("✅", key=f"select_{event_id}", help="Sudah tersimpan. Klik untuk lihat."):
                            st.session_state.selected_tournament = tournament
                            st.session_state.current_step = 'selection'
                            st.rerun()
                    elif is_nodata:
                        st.markdown("⚠️ No data")
                    else:
                        scrape_status = get_scrape_status()
                        with _scrape_lock:
                            bg = scrape_status.get(event_id, {})
                        bg_status = bg.get("status")
                        if bg_status == "running":
                            progress = bg.get("progress", 0)
                            total = bg.get("total", 0)
                            current_cat = bg.get("current_cat", "")
                            pct = int(progress / total * 100) if total > 0 else 0
                            st.progress(pct, text=f"{pct}%")
                            st.caption(f"{current_cat} — {bg.get('count', 0)} rec")
                        elif bg_status == "done":
                            st.markdown(f"✅ {bg.get('count', 0)}")
                        elif bg_status == "error":
                            st.markdown("❌ Error")
                        elif bg_status == "nodata":
                            st.markdown("⚠️ No data")
                        else:
                            if st.button("Scrape", key=f"scrape_{event_id}", type="primary"):
                                scrape_status = get_scrape_status()
                                with _scrape_lock:
                                    scrape_status[event_id] = {"status": "running", "count": 0, "error": "", "progress": 0, "total": 0, "current_cat": "Starting..."}
                                t_copy = dict(tournament)
                                year = st.session_state.selected_year
                                thread = threading.Thread(
                                    target=_scrape_tournament_bg,
                                    args=(event_id, t_copy, year, delay_min, delay_max, scrape_status),
                                    daemon=True
                                )
                                thread.start()
                                st.rerun()
                st.markdown("---")
        
        # Auto-refresh: if any scraping is running, wait briefly and rerun to update progress
        scrape_status = get_scrape_status()
        with _scrape_lock:
            has_running = any(v.get("status") == "running" for v in scrape_status.values())
        if has_running:
            time.sleep(2)
            st.rerun()
    else:
        st.warning("Tidak ada turnamen ditemukan untuk tahun ini.")
        st.info("Coba tahun lain atau periksa koneksi internet.")

elif st.session_state.current_step == 'batch_scraping':
    batch_list = st.session_state.get('batch_tournaments', [])
    st.header(f"⏳ Batch Scraping {len(batch_list)} Turnamen")
    
    if st.button("← Kembali", key="back_from_batch"):
        st.session_state.current_step = 'tournaments'
        st.rerun()
    
    if not batch_list:
        st.warning("Tidak ada turnamen dipilih.")
        if st.button("Kembali", key="back_batch_empty"):
            st.session_state.current_step = 'tournaments'
            st.rerun()
        st.stop()
    
    engine = IanseoScraperEngine(delay_range=(delay_min, delay_max))
    
    overall_progress = st.progress(0)
    status_text = st.empty()
    results_log = st.empty()
    
    batch_results = []
    total = len(batch_list)
    db = ArcheryDatabase()
    
    for idx, tournament in enumerate(batch_list):
        event_id = str(tournament.get('event_id', ''))
        event_name = tournament.get('event_name', 'Unknown')
        
        status_text.text(f"[{idx+1}/{total}] Scraping: {event_name[:50]}...")
        overall_progress.progress(int(idx / total * 100))
        
        try:
            detail_url = tournament.get('detail_url', f"https://www.ianseo.net/Details.php?toId={event_id}")
            detail_soup = engine.fetch_page(detail_url)
            
            if not detail_soup:
                batch_results.append({"event_id": event_id, "name": event_name, "status": "❌ Gagal fetch", "records": 0})
                continue
            
            nav_links = IanseoParser.extract_event_navigation(detail_soup)
            qual_links = nav_links["qualification_links"]
            
            if not qual_links and not nav_links["elimination_links"] and not nav_links["team_links"]:
                tournament["year"] = st.session_state.selected_year
                db.save_tournament(tournament, 0, status="no_results")
                batch_results.append({"event_id": event_id, "name": event_name, "status": "⚠️ No results", "records": 0})
                continue
            
            all_records = []
            for q_link in qual_links:
                cat_name = q_link["text"]
                url = q_link["url"]
                page_soup = engine.fetch_page(url)
                if page_soup:
                    records = IanseoParser.parse_scores_table(
                        page_soup, category_name=cat_name, round_type="Qualification",
                        tournament_info={
                            "year": st.session_state.selected_year,
                            "date": tournament.get('date', ''),
                            "location": tournament.get('location', ''),
                            "organizer": tournament.get('organizer', ''),
                            "event_name": event_name,
                        }
                    )
                    all_records.extend(records)
            
            if all_records:
                tournament["year"] = st.session_state.selected_year
                db.save_tournament(tournament, len(all_records))
                db.save_athletes(all_records, event_id)
                db.export_tournament_to_parquet(event_id)
                batch_results.append({"event_id": event_id, "name": event_name, "status": "✅ Sukses", "records": len(all_records)})
            else:
                tournament["year"] = st.session_state.selected_year
                db.save_tournament(tournament, 0, status="nodata")
                batch_results.append({"event_id": event_id, "name": event_name, "status": "⚠️ No data", "records": 0})
                
        except Exception as e:
            batch_results.append({"event_id": event_id, "name": event_name, "status": f"❌ Error: {str(e)[:50]}", "records": 0})
        
        # Update log
        log_lines = [f"{'Status':<12} {'Records':>8}  Name" for _ in range(1)]
        log_lines = []
        for r in batch_results:
            log_lines.append(f"{r['status']:<12} {r['records']:>8}  {r['name'][:60]}")
        results_log.text("\n".join(log_lines))
    
    overall_progress.progress(100)
    
    success_count = sum(1 for r in batch_results if r["status"].startswith("✅"))
    total_records = sum(r["records"] for r in batch_results)
    status_text.text(f"✅ Batch selesai! {success_count}/{total} turnamen berhasil, {total_records} total records")
    
    st.markdown("---")
    st.subheader("📊 Hasil Batch Scraping")
    df_batch = pd.DataFrame(batch_results)
    st.dataframe(df_batch, use_container_width=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📊 Lihat Big Data", type="primary"):
            st.session_state.view_mode = 'bigdata'
            st.session_state.current_step = 'year'
            st.rerun()
    with col2:
        if st.button("← Kembali ke Daftar", key="back_after_batch"):
            st.session_state.current_step = 'tournaments'
            st.rerun()

elif st.session_state.current_step == 'selection':
    tournament = st.session_state.selected_tournament
    st.header("📋 Pilih Data yang Akan Diambil")
    st.markdown(f"**Turnamen:** {tournament.get('event_name', 'Unknown')}")
    
    if st.button("← Kembali", key="back_to_tournaments"):
        st.session_state.current_step = 'tournaments'
        st.rerun()
    
    st.markdown("### Pilih Field Data")
    
    field_names = {
        'year': 'Year',
        'date_competition': 'Date Competition',
        'location': 'Location',
        'organizer': 'Organizer',
        'event_name': 'Event Name',
        'division': 'Division',
        'class': 'Class',
        'gender': 'Gender',
        'rank': 'Rank/Position',
        'distance': 'Distance (m)',
        'athlete_name': 'Athlete Name',
        'country': 'Country/Club',
        'distance_1': 'Distance 1 Score',
        'distance_2': 'Distance 2 Score',
        'distance_3': 'Distance 3 Score',
        'distance_4': 'Distance 4 Score',
        'distance_5': 'Distance 5 Score',
        'distance_6': 'Distance 6 Score',
        'distance_7': 'Distance 7 Score',
        'distance_8': 'Distance 8 Score',
        'distance_9': 'Distance 9 Score',
        'distance_10': 'Distance 10 Score',
        'arrows': 'Arrows',
        'total_score': 'Total Score',
        'index': 'Index (Score/Arrows)',
        'tens': '10s Count',
        'xs': 'Xs Count',
        'category': 'Category',
    }
    
    cols = st.columns(3)
    for i, (field_id, field_name) in enumerate(field_names.items()):
        col = cols[i % 3]
        with col:
            st.session_state.selected_fields[field_id] = st.checkbox(
                field_name,
                value=st.session_state.selected_fields.get(field_id, True),
                key=f"field_{field_id}"
            )
    
    st.markdown("---")
    if st.button("🚀 Mulai Scraping", type="primary", use_container_width=True):
        st.session_state.current_step = 'scraping'
        st.rerun()

elif st.session_state.current_step == 'scraping':
    tournament = st.session_state.selected_tournament
    st.header("⏳ Sedang Scraping...")
    st.markdown(f"Mengambil data dari: **{tournament.get('event_name', 'Unknown')}**")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Initialize engine
        status_text.text("Inisialisasi engine...")
        progress_bar.progress(10)
        time.sleep(0.5)
        
        engine = IanseoScraperEngine(delay_range=(delay_min, delay_max))
        event_id = tournament.get('event_id', '')
        
        # Step 1: Get tournament details
        status_text.text("Mengambil detail turnamen...")
        progress_bar.progress(20)
        time.sleep(0.5)
        
        detail_url = tournament.get('detail_url', f"https://www.ianseo.net/Details.php?toId={event_id}")
        detail_soup = engine.fetch_page(detail_url)
        
        if not detail_soup:
            st.error("Gagal mengambil detail turnamen")
            if st.button("Kembali", key="back_to_selection_fail"):
                st.session_state.current_step = 'selection'
                st.rerun()
            st.stop()
        
        # Step 2: Parse navigation
        status_text.text("Menganalisis struktur menu...")
        progress_bar.progress(40)
        time.sleep(0.5)
        
        nav_links = IanseoParser.extract_event_navigation(detail_soup)
        
        # Check if any results are available
        qualification_links = nav_links["qualification_links"]
        elimination_links = nav_links["elimination_links"]
        team_links = nav_links["team_links"]
        pdf_docs = nav_links["pdf_documents"]
        
        if not qualification_links and not elimination_links and not team_links:
            st.warning(
                f"⚠️ Turnamen **{tournament.get('event_name', 'Unknown')}** belum memiliki data hasil (qualification/elimination/team). "
                f"Hanya ditemukan {len(pdf_docs)} dokumen PDF dan link entries. "
                f"Pilih turnamen lain yang sudah memiliki hasil pertandingan."
            )
            if st.button("← Kembali", key="back_to_selection_no_results"):
                st.session_state.current_step = 'selection'
                st.rerun()
            st.stop()
        
        # Step 3: Extract data
        status_text.text("Mengekstrak data atlet...")
        progress_bar.progress(60)
        time.sleep(0.5)
        
        all_records = []
        qualification_links = nav_links["qualification_links"]
        
        if qualification_links:
            total_cats = len(qualification_links)
            for i, q_link in enumerate(qualification_links):
                status_text.text(f"Mengekstrak kategori {i+1}/{total_cats}: {q_link['text'][:40]}...")
                cat_name = q_link["text"]
                url = q_link["url"]
                
                page_soup = engine.fetch_page(url)
                if page_soup:
                    records = IanseoParser.parse_scores_table(
                        page_soup, 
                        category_name=cat_name, 
                        round_type="Qualification",
                        tournament_info={
                            "year": st.session_state.selected_year,
                            "date": tournament.get('date', ''),
                            "location": tournament.get('location', ''),
                            "organizer": tournament.get('organizer', ''),
                            "event_name": tournament.get('event_name', ''),
                        }
                    )
                    all_records.extend(records)
                    logger.info(f"Kategori '{cat_name}': {len(records)} records")
                
                progress = 60 + int((i + 1) / total_cats * 25)
                progress_bar.progress(progress)
        
        # Step 4: PDF extraction if enabled
        if enable_pdf and nav_links["pdf_documents"]:
            status_text.text("Mengekstrak data dari PDF...")
            progress_bar.progress(85)
            time.sleep(0.5)
            
            pdf_extractor = IanseoPDFExtractor()
            for pdf_link in nav_links["pdf_documents"][:2]:
                pdf_url = pdf_link["url"]
                pdf_name = f"event_{event_id}_{pdf_link['text'].replace(' ', '_')}.pdf"
                
                local_pdf_path = pdf_extractor.download_pdf(pdf_url, pdf_name)
                if local_pdf_path:
                    pdf_records = pdf_extractor.extract_table_from_pdf(
                        local_pdf_path, 
                        category_name=pdf_link["text"]
                    )
                    all_records.extend(pdf_records)
        
        # Step 5: Process data
        status_text.text("Memproses data ke DataFrame...")
        progress_bar.progress(95)
        time.sleep(0.5)
        
        if all_records:
            df = IanseoDataHandler.create_dataframe(all_records)
            
            # Filter selected fields
            selected_cols = [k for k, v in st.session_state.selected_fields.items() if v]
            available_cols = [col for col in selected_cols if col in df.columns]
            df_filtered = df[available_cols] if available_cols else df
            
            # Save to DuckDB
            status_text.text("💾 Menyimpan ke database...")
            tournament["year"] = st.session_state.selected_year
            db = ArcheryDatabase()
            db.save_tournament(tournament, len(all_records))
            db.save_athletes(all_records, event_id)
            db.export_tournament_to_parquet(event_id)
            
            st.session_state.scraping_results = {
                'dataframe': df_filtered,
                'total_records': len(all_records),
                'categories': df['category'].nunique() if 'category' in df.columns else 0,
                'tournament_name': tournament.get('event_name', 'Unknown'),
                'event_id': event_id
            }
            
            progress_bar.progress(100)
            status_text.text("✅ Scraping selesai!")
            
            time.sleep(1)
            st.session_state.current_step = 'results'
            st.rerun()
        else:
            st.error("Tidak ada data yang berhasil diekstrak")
            if st.button("Kembali", key="back_to_selection_no_data"):
                st.session_state.current_step = 'selection'
                st.rerun()
                
    except Exception as e:
        st.error(f"Terjadi error saat scraping: {str(e)}")
        if st.button("Kembali", key="back_to_selection_error"):
            st.session_state.current_step = 'selection'
            st.rerun()

elif st.session_state.current_step == 'results':
    results = st.session_state.scraping_results
    
    st.header("✅ Scraping Selesai!")
    st.markdown(f"**Turnamen:** {results['tournament_name']}")
    
    if st.button("🔄 Mulai Baru", key="start_new"):
        st.session_state.current_step = 'year'
        st.session_state.selected_year = ''
        st.session_state.selected_tournament = None
        st.session_state.scraping_results = None
        st.rerun()
    
    # Statistics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🎯 Atlet Diekstrak", results['total_records'])
    with col2:
        st.metric("🏷️ Kategori", results['categories'])
    with col3:
        st.metric("📊 Format", "3 (CSV, Excel, JSON)")
    
    st.markdown("---")
    
    # Data preview
    st.subheader("📋 Preview Data")
    df = results['dataframe']
    
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        
        # Export options
        st.markdown("---")
        st.subheader("💾 Download Data")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"ianseo_{results['event_id']}_{results['tournament_name'].replace(' ', '_')}.csv",
                mime='text/csv',
                use_container_width=True
            )
        
        with col2:
            excel_buffer = pd.ExcelWriter(f"ianseo_{results['event_id']}.xlsx", engine='openpyxl')
            df.to_excel(excel_buffer, index=False, sheet_name='Results')
            excel_buffer.close()
            
            with open(f"ianseo_{results['event_id']}.xlsx", 'rb') as f:
                excel_data = f.read()
            
            st.download_button(
                label="📥 Download Excel",
                data=excel_data,
                file_name=f"ianseo_{results['event_id']}_{results['tournament_name'].replace(' ', '_')}.xlsx",
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                use_container_width=True
            )
        
        with col3:
            json_data = df.to_json(orient='records', indent=2)
            st.download_button(
                label="📥 Download JSON",
                data=json_data,
                file_name=f"ianseo_{results['event_id']}_{results['tournament_name'].replace(' ', '_')}.json",
                mime='application/json',
                use_container_width=True
            )
    else:
        st.warning("Data kosong")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #6b7280; font-size: 0.8rem;'>
    Ianseo Archery Scraper • 2026 • Python + Streamlit
</div>
""", unsafe_allow_html=True)
