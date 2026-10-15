export interface ArcheryEvent {
  id: string;
  name: string;
  date: string;
  location: string;
  categories: string[];
}

export interface AthleteRecord {
  rank: number;
  back_no: string;
  athlete_name: string;
  club_provinsi: string;
  distance_1: number;
  distance_2: number;
  total_score: number;
  tens: number;
  xs: number;
  category: string;
  round: string;
}

export interface ScrapeSimulationLog {
  timestamp: string;
  type: 'info' | 'success' | 'warning' | 'error' | 'fetching';
  message: string;
}

export const mockEvents: ArcheryEvent[] = [
  {
    id: "17290",
    name: "Piala Presiden Panahan Republik Indonesia 2024",
    date: "24-28 Jun 2024",
    location: "Jakarta, DKI Jakarta",
    categories: ["Recurve Men", "Recurve Women", "Compound Men", "Compound Women", "National/Standard Bow Men"]
  },
  {
    id: "16845",
    name: "Kejuaraan Nasional Panahan Senior 2023",
    date: "18-24 Nov 2023",
    location: "Sleman, DI Yogyakarta",
    categories: ["Recurve Men", "Recurve Women", "Compound Men", "Compound Women", "Barebow Men", "Barebow Women"]
  },
  {
    id: "18102",
    name: "Sirkuit Nasional Panahan Stage 1 2024",
    date: "04-10 Mar 2024",
    location: "Surabaya, Jawa Timur",
    categories: ["Recurve Men", "Recurve Women", "Compound Men", "Compound Women", "Barebow Men"]
  },
  {
    id: "15911",
    name: "Bogor Open Archery Championship 2023",
    date: "01-05 Jul 2023",
    location: "Bogor, Jawa Barat",
    categories: ["National Under-15 Men", "National Under-15 Women", "Compound Men", "Barebow Master Men"]
  }
];

export const mockAthleteData: Record<string, AthleteRecord[]> = {
  "17290": [
    { rank: 1, back_no: "12A", athlete_name: "Arif Dwi Pangestu", club_provinsi: "DKI Jakarta (DKI)", distance_1: 342, distance_2: 345, total_score: 687, tens: 41, xs: 18, category: "Recurve Men", round: "Qualification" },
    { rank: 2, back_no: "12B", athlete_name: "Riau Ega Agatha", club_provinsi: "Jawa Timur (JATIM)", distance_1: 338, distance_2: 341, total_score: 679, tens: 36, xs: 15, category: "Recurve Men", round: "Qualification" },
    { rank: 3, back_no: "13A", athlete_name: "Alviyanto Bagas Prastyadi", club_provinsi: "Jawa Tengah (JATENG)", distance_1: 335, distance_2: 338, total_score: 673, tens: 33, xs: 12, category: "Recurve Men", round: "Qualification" },
    { rank: 4, back_no: "13C", athlete_name: "Ahmad Khoirul Anam", club_provinsi: "Jawa Barat (JABAR)", distance_1: 330, distance_2: 332, total_score: 662, tens: 28, xs: 10, category: "Recurve Men", round: "Qualification" },
    { rank: 5, back_no: "14B", athlete_name: "RM Gusti Fazli", club_provinsi: "DI Yogyakarta (DIY)", distance_1: 328, distance_2: 330, total_score: 658, tens: 26, xs: 9, category: "Recurve Men", round: "Qualification" },
    
    { rank: 1, back_no: "04A", athlete_name: "Diananda Choirunisa", club_provinsi: "Jawa Timur (JATIM)", distance_1: 335, distance_2: 339, total_score: 674, tens: 35, xs: 14, category: "Recurve Women", round: "Qualification" },
    { rank: 2, back_no: "04C", athlete_name: "Rezza Octavia", club_provinsi: "DKI Jakarta (DKI)", distance_1: 329, distance_2: 331, total_score: 660, tens: 27, xs: 11, category: "Recurve Women", round: "Qualification" },
    { rank: 3, back_no: "05B", athlete_name: "Anisyadhira Clarabella", club_provinsi: "Jawa Barat (JABAR)", distance_1: 322, distance_2: 325, total_score: 647, tens: 22, xs: 8, category: "Recurve Women", round: "Qualification" },
    
    { rank: 1, back_no: "22A", athlete_name: "Prima Wisnu Wardhana", club_provinsi: "DI Yogyakarta (DIY)", distance_1: 352, distance_2: 355, total_score: 707, tens: 59, xs: 28, category: "Compound Men", round: "Qualification" },
    { rank: 2, back_no: "22B", athlete_name: "Deki Adika Hastian", club_provinsi: "Jawa Barat (JABAR)", distance_1: 349, distance_2: 354, total_score: 703, tens: 55, xs: 24, category: "Compound Men", round: "Qualification" },
    { rank: 3, back_no: "23C", athlete_name: "Hendika Pratama Putra", club_provinsi: "DKI Jakarta (DKI)", distance_1: 348, distance_2: 350, total_score: 698, tens: 51, xs: 20, category: "Compound Men", round: "Qualification" }
  ],
  "16845": [
    { rank: 1, back_no: "08A", athlete_name: "Arif Dwi Pangestu", club_provinsi: "DKI Jakarta (DKI)", distance_1: 339, distance_2: 342, total_score: 681, tens: 38, xs: 16, category: "Recurve Men", round: "Qualification" },
    { rank: 2, back_no: "08B", athlete_name: "Alviyanto Bagas Prastyadi", club_provinsi: "Jawa Tengah (JATENG)", distance_1: 332, distance_2: 336, total_score: 668, tens: 30, xs: 11, category: "Recurve Men", round: "Qualification" },
    { rank: 3, back_no: "09A", athlete_name: "Riau Ega Agatha", club_provinsi: "Jawa Timur (JATIM)", distance_1: 330, distance_2: 334, total_score: 664, tens: 29, xs: 10, category: "Recurve Men", round: "Qualification" },
    
    { rank: 1, back_no: "28A", athlete_name: "Aulia Agastya", club_provinsi: "Kalimantan Timur (KALTIM)", distance_1: 312, distance_2: 318, total_score: 630, tens: 18, xs: 7, category: "Barebow Men", round: "Qualification" },
    { rank: 2, back_no: "28C", athlete_name: "Heri Purwanto", club_provinsi: "Jawa Barat (JABAR)", distance_1: 309, distance_2: 311, total_score: 620, tens: 15, xs: 5, category: "Barebow Men", round: "Qualification" },
    { rank: 3, back_no: "29B", athlete_name: "Rahmat Sulistyo", club_provinsi: "DKI Jakarta (DKI)", distance_1: 305, distance_2: 308, total_score: 613, tens: 12, xs: 4, category: "Barebow Men", round: "Qualification" }
  ],
  "18102": [
    { rank: 1, back_no: "10A", athlete_name: "Riau Ega Agatha", club_provinsi: "Jawa Timur (JATIM)", distance_1: 341, distance_2: 344, total_score: 685, tens: 40, xs: 19, category: "Recurve Men", round: "Qualification" },
    { rank: 2, back_no: "10B", athlete_name: "Ahmad Khoirul Anam", club_provinsi: "Jawa Barat (JABAR)", distance_1: 334, distance_2: 338, total_score: 672, tens: 32, xs: 13, category: "Recurve Men", round: "Qualification" },
    
    { rank: 1, back_no: "16C", athlete_name: "Syahara Khoerunisa", club_provinsi: "Banten (BTN)", distance_1: 346, distance_2: 348, total_score: 694, tens: 47, xs: 21, category: "Compound Women", round: "Qualification" },
    { rank: 2, back_no: "17A", athlete_name: "Ratih Zilizati Fadhly", club_provinsi: "Jawa Barat (JABAR)", distance_1: 342, distance_2: 345, total_score: 687, tens: 41, xs: 18, category: "Compound Women", round: "Qualification" }
  ],
  "15911": [
    { rank: 1, back_no: "02A", athlete_name: "Muhammad Faiz", club_provinsi: "Fast Archery Club", distance_1: 310, distance_2: 315, total_score: 625, tens: 14, xs: 5, category: "National Under-15 Men", round: "Qualification" },
    { rank: 2, back_no: "02B", athlete_name: "Fathir Azzam", club_provinsi: "Bogor Archery Club", distance_1: 305, distance_2: 308, total_score: 613, tens: 11, xs: 3, category: "National Under-15 Men", round: "Qualification" }
  ]
};

export const generateSimulationLogs = (
  eventId: string, 
  countryId: string, 
  delay: number, 
  pdfEnabled: boolean
): ScrapeSimulationLog[] => {
  const event = mockEvents.find(e => e.id === eventId) || mockEvents[0];
  const logs: ScrapeSimulationLog[] = [];
  
  const addLog = (msg: string, type: ScrapeSimulationLog['type'] = 'info') => {
    const now = new Date().toISOString().replace('T', ' ').substring(0, 19);
    logs.push({ timestamp: now, type, message: msg });
  };

  addLog(`Memulai IanseoScraperEngine...`, 'info');
  addLog(`User-Agent acak berhasil dimuat (Chrome 120.0.0.0 pada Windows NT 10.0)`, 'success');
  addLog(`Konfigurasi: Delay = [${delay.toFixed(1)}s - ${(delay + 1.5).toFixed(1)}s], CountryID = ${countryId}, Timeout = 15s`, 'info');
  
  addLog(`[LEVEL 1] Menghubungi URL utama: https://www.ianseo.net/TourList.php?countryid=${countryId}`, 'fetching');
  addLog(`Menerima respon dari TourList.php dengan kode status HTTP 200 OK`, 'success');
  addLog(`Berhasil mengurai daftar event. Ditemukan 4 turnamen panahan Indonesia aktif.`, 'success');
  
  addLog(`[LEVEL 2] Menghubungi URL detail event: https://www.ianseo.net/Tournament.php?id=${eventId}`, 'fetching');
  addLog(`Parsing halaman detail event: "${event.name}"...`, 'info');
  addLog(`Menganalisis link navigasi hasil skor di sidebar & menu...`, 'info');
  
  const qualCount = event.categories.length;
  addLog(`Menemukan ${qualCount} Kategori Kualifikasi HTML (ResultList.php)`, 'success');
  addLog(`Menemukan ${Math.max(1, qualCount - 2)} Kategori Eliminasi HTML (Official.php)`, 'success');
  addLog(`Menemukan ${pdfEnabled ? '2' : '0'} tautan file PDF Buku Hasil Turnamen (Book.php / PDF)`, 'success');

  // Menstimulasi fetch per kategori
  event.categories.forEach((cat, index) => {
    addLog(`[LEVEL 3] Menghubungi URL Kualifikasi: ResultList.php?id=${eventId}&Class=${cat.replace(' ', '')}`, 'fetching');
    addLog(`Mengurai tabel skor kualifikasi untuk kategori "${cat}"...`, 'info');
    const athletes = mockAthleteData[eventId]?.filter(a => a.category === cat) || [];
    addLog(`Sukses: Berhasil mengekstrak ${athletes.length || 3} data atlet dan skor untuk kategori "${cat}"`, 'success');
  });

  if (pdfEnabled) {
    addLog(`[LEVEL 3 - PDF] Menghubungi tautan dokumen hasil: https://www.ianseo.net/TourFiles/Book_${eventId}.pdf`, 'fetching');
    addLog(`Mengunduh file PDF hasil turnamen...`, 'info');
    addLog(`File PDF disimpan sementara di folder lokal 'downloaded_results/'`, 'success');
    addLog(`Mengaktifkan engine 'pdfplumber' untuk ekstraksi data tabel PDF...`, 'info');
    addLog(`Sukses: Berhasil membaca PDF Halaman 1-4. Diekstrak tambahan 8 data atlet/skor.`, 'success');
  }

  addLog(`[DATAFRAME] Mentransfer seluruh records (Total: ${mockAthleteData[eventId]?.length || 10} baris) ke dalam Pandas DataFrame...`, 'info');
  addLog(`Melakukan pembersihan data tipe numerik (Rank, Total Score, Tens, Xs, Distances)...`, 'info');
  addLog(`Menyortir hasil data berdasarkan [Kategori (A-Z), Total Score (Menurun)]`, 'success');
  
  addLog(`Mengekspor Pandas DataFrame ke folder output_data/...`, 'info');
  addLog(`[-] File CSV berhasil disimpan: output_data/ianseo_${eventId}_${event.name.substring(0, 15).replace(/\s+/g, '_')}.csv`, 'success');
  addLog(`[-] File Excel Multi-Sheet berhasil disimpan: output_data/ianseo_${eventId}_${event.name.substring(0, 15).replace(/\s+/g, '_')}.xlsx`, 'success');
  addLog(`[-] File JSON berhasil disimpan: output_data/ianseo_${eventId}_${event.name.substring(0, 15).replace(/\s+/g, '_')}.json`, 'success');
  
  addLog(`========================================================================`, 'info');
  addLog(`PROSES SCRAPING BERHASIL DISELESAIKAN SECARA SEMPURNA!`, 'success');
  addLog(`========================================================================`, 'success');

  return logs;
};
