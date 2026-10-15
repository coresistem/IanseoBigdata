import time
import random
import re
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

    def scrape_indonesian_events(self, year: str = None, comptime: str = None, time_type: str = None) -> List[Dict[str, Any]]:
        """
        LEVEL 1: Mengambil daftar turnamen dari Indonesia.
        URL Target: TourList.php?countryid=INA&Year=2026&comptime=&timeType=local
        
        Args:
            year (str): Tahun turnamen (misal: "2026")
            comptime (str): Filter waktu kompetisi
            time_type (str): Tipe waktu (misal: "local")
        """
        # Build full URL dengan query string
        # Gunakan full URL lengkap dengan https dan parameter yang benar
        # Sesuai format dari user: https://www.ianseo.net/TourList.php?Year=2026&countryid=INA&comptime=&timeType=local
        if year:
            target_url = f"https://www.ianseo.net/TourList.php?Year={year}&countryid=INA"
        else:
            target_url = "https://www.ianseo.net/TourList.php?countryid=INA"
        
        if comptime is not None:
            target_url += f"&comptime={comptime}"
        if time_type:
            target_url += f"&timeType={time_type}"
        
        # Bypass fetch_page dan gunakan requests langsung untuk testing
        # Tambahkan cookie dan session management
        try:
            logger.info(f"Direct request ke: {target_url}")
            
            # Update headers untuk lebih mirip browser
            headers = self._get_headers()
            headers.update({
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
                "Cache-Control": "max-age=0",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1"
            })
            
            response = self.session.get(
                target_url,
                headers=headers,
                timeout=self.timeout,
                allow_redirects=True
            )
            response.raise_for_status()
            
            # Log response info
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response URL: {response.url}")
            logger.info(f"Content length: {len(response.content)}")
            
            soup = BeautifulSoup(response.content, "lxml")
        except Exception as e:
            logger.error(f"Direct request gagal: {e}")
            return []
        
        events = []
        
        if not soup:
            logger.error("Gagal mendapatkan daftar event Indonesia.")
            return events

        # Debug: Log URL yang diakses
        logger.info(f"URL yang diakses: {target_url}")
        
        # Debug: Log HTML structure
        logger.info(f"HTML title: {soup.title.string if soup.title else 'N/A'}")
        logger.info(f"HTML tables found: {len(soup.find_all('table'))}")
        
        # Ianseo menaruh daftar turnamen di dalam tabel dengan class 'tourlist-table'
        table = soup.find("table", {"class": "tourlist-table"}) or soup.find("table")
        
        if not table:
            logger.warning("Tabel turnamen tidak ditemukan di halaman.")
            return events
            
        rows = table.find_all("tr")
        logger.info(f"Ditemukan {len(rows)} baris data potensial.")

        # Ianseo menggunakan onclick pada <tr> untuk link turnamen:
        # onclick="window.open('Details.php?toId=28831','_self')"
        # Struktur 11 kolom:
        # col0: kosong, col1: kosong (mobile), col2: event_code, col3: event_name,
        # col4: event_name (dup), col5: kosong, col6: organizer, col7: flag img,
        # col8: location, col9: date, col10: updated
        for row in rows:
            # Lewati baris header
            if row.find("th"):
                continue
                
            cols = row.find_all("td")
            
            # Skip baris detail (2 kolom: location/updated detail)
            if len(cols) < 5:
                continue
                
            # Ambil event ID dari onclick attribute pada <tr>
            onclick = row.get("onclick", "")
            event_id = ""
            event_url = ""
            
            if onclick:
                # Pattern: window.open('Details.php?toId=28831','_self')
                match = re.search(r"Details\.php\?toId=(\d+)", onclick)
                if match:
                    event_id = match.group(1)
                    event_url = f"https://www.ianseo.net/Details.php?toId={event_id}"
            
            if not event_id:
                continue
                
            try:
                # Extract data dari 11 kolom
                event_code = cols[2].get_text(strip=True) if len(cols) > 2 else ""
                event_name = cols[3].get_text(strip=True) if len(cols) > 3 else "N/A"
                organizer_val = cols[6].get_text(strip=True) if len(cols) > 6 else "N/A"
                location_val = cols[8].get_text(strip=True) if len(cols) > 8 else "N/A"
                date_val = cols[9].get_text(strip=True) if len(cols) > 9 else "N/A"
                
                event_data = {
                    "event_id": event_id,
                    "event_code": event_code,
                    "event_name": event_name,
                    "organizer": organizer_val,
                    "date": date_val,
                    "location": location_val,
                    "detail_url": event_url
                }
                events.append(event_data)
                logger.info(f"Sukses Ekstrak Event: [{event_id}] {event_code} - {event_name}")
            except Exception as e:
                logger.error(f"Gagal memparsing baris event: {e}")
                    
        logger.info(f"Total event berhasil diekstrak: {len(events)}")
        return events
