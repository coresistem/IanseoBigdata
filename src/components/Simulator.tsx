import React, { useState, useEffect, useRef } from 'react';
import { mockEvents, mockAthleteData, generateSimulationLogs, AthleteRecord, ArcheryEvent, ScrapeSimulationLog } from '../data/mockScrapeData';
import { Play, RotateCcw, AlertTriangle, ShieldCheck, FileDown, Layers, Sliders, Server, Filter, Search, Terminal, Eye, CheckCircle2 } from 'lucide-react';

export default function Simulator() {
  const [selectedEventId, setSelectedEventId] = useState<string>("17290");
  const [countryId, setCountryId] = useState<string>("INA");
  const [delay, setDelay] = useState<number>(1.5);
  const [pdfEnabled, setPdfEnabled] = useState<boolean>(true);
  
  // Scraper status: 'idle' | 'scraping' | 'completed' | 'error'
  const [status, setStatus] = useState<'idle' | 'scraping' | 'completed' | 'error'>('idle');
  const [logs, setLogs] = useState<ScrapeSimulationLog[]>([]);
  const [visibleLogsCount, setVisibleLogsCount] = useState<number>(0);
  const [progress, setProgress] = useState<number>(0);
  
  // Filter states
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [categoryFilter, setCategoryFilter] = useState<string>("ALL");
  const [clubFilter, setClubFilter] = useState<string>("ALL");

  const terminalEndRef = useRef<HTMLDivElement>(null);
  const logIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const eventDetail = mockEvents.find(e => e.id === selectedEventId) || mockEvents[0];
  const athletes = mockAthleteData[selectedEventId] || [];

  // Get unique clubs for filtering
  const uniqueClubs = Array.from(new Set(athletes.map(a => {
    // extract short province or club
    const match = a.club_provinsi.match(/\(([^)]+)\)/);
    return match ? match[1] : a.club_provinsi;
  })));

  useEffect(() => {
    if (terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [visibleLogsCount, status]);

  const handleStartScrape = () => {
    setStatus('scraping');
    setLogs([]);
    setVisibleLogsCount(0);
    setProgress(0);
    setSearchTerm("");
    setCategoryFilter("ALL");
    setClubFilter("ALL");

    // Pre-generate the complete log array based on selected event and settings
    const fullLogs = generateSimulationLogs(selectedEventId, countryId, delay, pdfEnabled);
    setLogs(fullLogs);

    let currentLogIndex = 0;
    
    if (logIntervalRef.current) {
      clearInterval(logIntervalRef.current);
    }

    logIntervalRef.current = setInterval(() => {
      currentLogIndex++;
      setVisibleLogsCount(currentLogIndex);
      setProgress(Math.round((currentLogIndex / fullLogs.length) * 100));

      if (currentLogIndex >= fullLogs.length) {
        if (logIntervalRef.current) clearInterval(logIntervalRef.current);
        setStatus('completed');
      }
    }, 400); // 400ms interval for natural terminal typing output feel
  };

  const handleReset = () => {
    if (logIntervalRef.current) {
      clearInterval(logIntervalRef.current);
    }
    setStatus('idle');
    setLogs([]);
    setVisibleLogsCount(0);
    setProgress(0);
  };

  useEffect(() => {
    return () => {
      if (logIntervalRef.current) {
        clearInterval(logIntervalRef.current);
      }
    };
  }, []);

  // Filter athletes
  const filteredAthletes = athletes.filter(ath => {
    const matchesSearch = ath.athlete_name.toLowerCase().includes(searchTerm.toLowerCase()) || 
                          ath.club_provinsi.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = categoryFilter === "ALL" || ath.category === categoryFilter;
    
    const clubShort = ath.club_provinsi.match(/\(([^)]+)\)/)?.[1] || ath.club_provinsi;
    const matchesClub = clubFilter === "ALL" || clubShort === clubFilter;
    
    return matchesSearch && matchesCategory && matchesClub;
  });

  const downloadCSV = () => {
    // Generate CSV content
    const headers = ["Rank", "BackNo", "Athlete Name", "Club/Provinsi", "Distance 1", "Distance 2", "Total Score", "10s", "Xs", "Category", "Round"];
    const rows = filteredAthletes.map(a => [
      a.rank,
      a.back_no,
      `"${a.athlete_name}"`,
      `"${a.club_provinsi}"`,
      a.distance_1,
      a.distance_2,
      a.total_score,
      a.tens,
      a.xs,
      `"${a.category}"`,
      `"${a.round}"`
    ]);

    const csvContent = [headers.join(","), ...rows.map(e => e.join(","))].join("\n");
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `ianseo_scraped_${selectedEventId}_${categoryFilter.replace(/\s+/g, '_')}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div id="scraper-simulator-root" className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      
      {/* LEFT: Configuration Panel (4 cols) */}
      <div className="lg:col-span-4 flex flex-col gap-5">
        <div className="bg-zinc-900/60 border border-zinc-800 rounded-xl p-5 shadow-lg backdrop-blur-md">
          <div className="flex items-center gap-2 mb-4 border-b border-zinc-800 pb-3">
            <Sliders className="w-5 h-5 text-emerald-400" />
            <h3 className="font-semibold text-sm text-zinc-100 uppercase tracking-wider">Scraper Parameters</h3>
          </div>

          <div className="space-y-4 text-xs">
            {/* Event Selector */}
            <div>
              <label className="block text-zinc-400 font-medium mb-1.5">Target Turnamen (Level 1):</label>
              <select
                id="select-target-event"
                value={selectedEventId}
                onChange={(e) => setSelectedEventId(e.target.value)}
                disabled={status === 'scraping'}
                className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2.5 text-zinc-200 font-medium focus:outline-none focus:border-emerald-500/50 disabled:opacity-50"
              >
                {mockEvents.map(event => (
                  <option key={event.id} value={event.id}>
                    [{event.id}] {event.name.length > 40 ? `${event.name.substring(0, 40)}...` : event.name}
                  </option>
                ))}
              </select>
              <p className="text-[10px] text-zinc-500 mt-1 leading-normal">
                Memilih ID turnamen yang akan ditembak langsung ke URL detail event Ianseo.
              </p>
            </div>

            {/* Country ID */}
            <div>
              <label className="block text-zinc-400 font-medium mb-1.5">Country ID (Filter Nasional):</label>
              <input
                id="input-country-id"
                type="text"
                value={countryId}
                onChange={(e) => setCountryId(e.target.value.toUpperCase())}
                disabled={status === 'scraping'}
                className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2.5 text-zinc-200 font-mono focus:outline-none focus:border-emerald-500/50 disabled:opacity-50"
              />
              <p className="text-[10px] text-zinc-500 mt-1">
                Default <code className="text-emerald-400 font-mono">INA</code> untuk daftar turnamen Indonesia.
              </p>
            </div>

            {/* Request Delay Slider */}
            <div>
              <div className="flex justify-between text-zinc-400 font-medium mb-1.5">
                <span>Request Delay Dinamis:</span>
                <span className="text-emerald-400 font-mono">{delay.toFixed(1)}s - {(delay + 1.5).toFixed(1)}s</span>
              </div>
              <input
                id="slider-request-delay"
                type="range"
                min="0.5"
                max="4.0"
                step="0.5"
                value={delay}
                onChange={(e) => setDelay(parseFloat(e.target.value))}
                disabled={status === 'scraping'}
                className="w-full accent-emerald-500 bg-zinc-800 rounded-lg appearance-none h-1 cursor-pointer disabled:opacity-40"
              />
              <p className="text-[10px] text-zinc-500 mt-1 leading-normal">
                Etika Scraping: Menghindari deteksi IP rate-limit dengan jeda acak di setiap HTTP GET request.
              </p>
            </div>

            {/* PDF Fallback Toggle */}
            <div className="flex items-center justify-between p-3 bg-zinc-950 rounded-lg border border-zinc-800/80">
              <div className="pr-2">
                <span className="block font-medium text-zinc-300">Ekstraksi Hasil PDF</span>
                <span className="text-[10px] text-zinc-500 leading-normal block mt-0.5">
                  Gunakan <code className="text-zinc-300 font-mono">pdfplumber</code> jika tabel HTML tidak tersedia.
                </span>
              </div>
              <input
                id="toggle-pdf-extraction"
                type="checkbox"
                checked={pdfEnabled}
                onChange={(e) => setPdfEnabled(e.target.checked)}
                disabled={status === 'scraping'}
                className="w-4 h-4 rounded text-emerald-600 bg-zinc-900 border-zinc-800 focus:ring-emerald-500 cursor-pointer disabled:opacity-40"
              />
            </div>
          </div>

          {/* Action Buttons */}
          <div className="mt-5 pt-4 border-t border-zinc-800/80 flex gap-3">
            {status !== 'scraping' && status !== 'completed' ? (
              <button
                id="btn-start-scraping-simulation"
                onClick={handleStartScrape}
                className="flex-1 flex items-center justify-center gap-2 py-3 px-4 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded-lg text-xs tracking-wider uppercase transition-colors shadow-md hover:shadow-emerald-900/20"
              >
                <Play className="w-4 h-4 fill-white" />
                Jalankan Scraper
              </button>
            ) : (
              <button
                id="btn-reset-scraping-simulation"
                onClick={handleReset}
                className={`flex-1 flex items-center justify-center gap-2 py-3 px-4 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 font-semibold rounded-lg text-xs tracking-wider uppercase transition-colors border border-zinc-700 ${status === 'scraping' ? 'opacity-80' : ''}`}
              >
                <RotateCcw className="w-4 h-4" />
                {status === 'scraping' ? 'Hentikan / Reset' : 'Reset Engine'}
              </button>
            )}
          </div>
        </div>

        {/* Informative Stats Card */}
        <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-4 text-xs leading-relaxed text-zinc-400">
          <div className="flex gap-2 items-start">
            <Server className="w-4 h-4 mt-0.5 text-emerald-500 shrink-0" />
            <div>
              <span className="font-semibold text-zinc-200 block mb-0.5">Penjelasan Simulasi</span>
              Karena kebijakan kebijakan CORS browser dan proteksi anti-scraping Cloudflare pada situs Ianseo, penarikan data langsung di browser sering diblokir. Simulator ini memodelkan seluruh logika scraping Python secara akurat, menggunakan representasi data real dari turnamen panahan Indonesia untuk melatih pemahaman alur kerja Anda.
            </div>
          </div>
        </div>
      </div>

      {/* RIGHT: Terminal & Results Grid (8 cols) */}
      <div className="lg:col-span-8 flex flex-col gap-6">
        
        {/* Terminal logs (active during scraping or when completed) */}
        <div className="bg-zinc-950 border border-zinc-800 rounded-xl overflow-hidden shadow-2xl flex flex-col">
          {/* Terminal Header */}
          <div className="bg-zinc-900 px-4 py-2.5 flex items-center justify-between border-b border-zinc-800">
            <div className="flex items-center gap-2">
              <div className="flex gap-1.5">
                <span className="w-3 h-3 rounded-full bg-red-500/80 block"></span>
                <span className="w-3 h-3 rounded-full bg-yellow-500/80 block"></span>
                <span className="w-3 h-3 rounded-full bg-emerald-500/80 block"></span>
              </div>
              <div className="flex items-center gap-1.5 ml-4">
                <Terminal className="w-3.5 h-3.5 text-emerald-400" />
                <span className="font-mono text-xs text-zinc-400 font-medium">ianseo_scraper_engine_cli.py</span>
              </div>
            </div>
            
            {status === 'scraping' && (
              <div className="flex items-center gap-2 text-[10px] font-mono text-emerald-400 animate-pulse">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block"></span>
                Scraping... {progress}%
              </div>
            )}
          </div>

          {/* Terminal Console */}
          <div className="p-4 font-mono text-xs h-64 overflow-y-auto bg-zinc-950/90 leading-relaxed space-y-1.5 scrollbar-thin">
            {logs.length === 0 ? (
              <div className="text-zinc-500 italic h-full flex items-center justify-center flex-col gap-2">
                <Terminal className="w-8 h-8 text-zinc-700" />
                <span>Tekan "Jalankan Scraper" untuk meluncurkan log pencarian data.</span>
              </div>
            ) : (
              logs.slice(0, visibleLogsCount).map((log, idx) => {
                let colorClass = "text-zinc-300";
                let prefix = "[INFO]";
                if (log.type === 'success') {
                  colorClass = "text-emerald-400";
                  prefix = "[SUCCESS]";
                } else if (log.type === 'warning') {
                  colorClass = "text-yellow-400";
                  prefix = "[WARN]";
                } else if (log.type === 'error') {
                  colorClass = "text-red-400";
                  prefix = "[ERROR]";
                } else if (log.type === 'fetching') {
                  colorClass = "text-blue-400";
                  prefix = "[FETCH]";
                }

                return (
                  <div key={idx} className="flex gap-3 items-start border-l border-zinc-900 pl-2">
                    <span className="text-[10px] text-zinc-600 shrink-0">{log.timestamp.split(' ')[1]}</span>
                    <span className={`font-semibold shrink-0 text-[10px] ${colorClass}`}>{prefix}</span>
                    <span className="text-zinc-300 break-all">{log.message}</span>
                  </div>
                );
              })
            )}
            <div ref={terminalEndRef} />
          </div>

          {/* Progress Bar */}
          {status === 'scraping' && (
            <div className="w-full bg-zinc-900 h-1">
              <div 
                className="bg-emerald-500 h-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              ></div>
            </div>
          )}
        </div>

        {/* Results Data Table (Visible after completed scraping) */}
        {status === 'completed' && (
          <div className="bg-zinc-900/40 border border-zinc-800 rounded-xl p-5 shadow-lg space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-800 pb-4">
              <div className="flex items-center gap-2.5">
                <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                <div>
                  <h4 className="font-semibold text-sm text-zinc-100">Scraped Pandas DataFrame</h4>
                  <p className="text-[10px] text-zinc-500">Merapikan data mentah Ianseo dengan Pandas untuk kebutuhan analisis statistik.</p>
                </div>
              </div>

              {/* CSV Export Button */}
              <button
                id="btn-download-scraped-csv"
                onClick={downloadCSV}
                className="flex items-center justify-center gap-2 py-2 px-3.5 bg-emerald-600/10 hover:bg-emerald-600/20 text-emerald-400 border border-emerald-500/20 rounded-lg text-xs font-semibold tracking-wide transition-all shadow-sm"
              >
                <FileDown className="w-4 h-4" />
                Ekspor CSV Hasil
              </button>
            </div>

            {/* Interactive Filters Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {/* Search input */}
              <div className="relative">
                <Search className="absolute left-2.5 top-2.5 w-4 h-4 text-zinc-500" />
                <input
                  id="search-athletes-input"
                  type="text"
                  placeholder="Cari atlet / klub..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 bg-zinc-950 border border-zinc-800 rounded-lg text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-emerald-500/50 transition-colors"
                />
              </div>

              {/* Category Filter */}
              <div>
                <select
                  id="filter-category-select"
                  value={categoryFilter}
                  onChange={(e) => setCategoryFilter(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2 text-xs text-zinc-200 focus:outline-none focus:border-emerald-500/50"
                >
                  <option value="ALL">Semua Kategori ({eventDetail.categories.length})</option>
                  {eventDetail.categories.map(cat => (
                    <option key={cat} value={cat}>{cat}</option>
                  ))}
                </select>
              </div>

              {/* Club / Province Filter */}
              <div>
                <select
                  id="filter-club-select"
                  value={clubFilter}
                  onChange={(e) => setClubFilter(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2 text-xs text-zinc-200 focus:outline-none focus:border-emerald-500/50"
                >
                  <option value="ALL">Semua Klub/Provinsi ({uniqueClubs.length})</option>
                  {uniqueClubs.map(club => (
                    <option key={club} value={club}>{club}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Results Table View */}
            <div className="border border-zinc-800/80 rounded-lg overflow-hidden bg-zinc-950">
              <div className="overflow-x-auto max-h-96">
                <table id="athletes-data-table" className="w-full text-left border-collapse text-xs">
                  <thead className="bg-zinc-900 text-zinc-400 font-medium border-b border-zinc-800 sticky top-0">
                    <tr>
                      <th className="p-3 text-center w-12">Rank</th>
                      <th className="p-3 text-center w-16">No Target</th>
                      <th className="p-3 min-w-[150px]">Nama Atlet</th>
                      <th className="p-3">Klub / Provinsi</th>
                      <th className="p-3 text-center">Jarak 1</th>
                      <th className="p-3 text-center">Jarak 2</th>
                      <th className="p-3 text-center font-semibold text-emerald-400">Total</th>
                      <th className="p-3 text-center">10s</th>
                      <th className="p-3 text-center">Xs</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800/50 text-zinc-300">
                    {filteredAthletes.map((ath, idx) => {
                      // Alternate row background styles
                      const isTopThree = ath.rank <= 3;
                      const badgeColor = ath.rank === 1 ? 'bg-amber-500/20 text-amber-400 border-amber-500/30' : 
                                         ath.rank === 2 ? 'bg-zinc-400/20 text-zinc-300 border-zinc-400/30' : 
                                         ath.rank === 3 ? 'bg-amber-700/20 text-amber-600 border-amber-700/30' : '';

                      return (
                        <tr key={idx} className="hover:bg-zinc-900/30 transition-colors">
                          <td className="p-3 text-center font-semibold">
                            {isTopThree ? (
                              <span className={`px-2 py-0.5 rounded border text-[11px] font-mono ${badgeColor}`}>
                                {ath.rank}
                              </span>
                            ) : (
                              <span className="text-zinc-500">{ath.rank}</span>
                            )}
                          </td>
                          <td className="p-3 text-center font-mono text-zinc-400">{ath.back_no}</td>
                          <td className="p-3 font-semibold text-zinc-100">{ath.athlete_name}</td>
                          <td className="p-3 text-zinc-400">{ath.club_provinsi}</td>
                          <td className="p-3 text-center font-mono">{ath.distance_1}</td>
                          <td className="p-3 text-center font-mono">{ath.distance_2}</td>
                          <td className="p-3 text-center font-mono font-bold text-emerald-400">{ath.total_score}</td>
                          <td className="p-3 text-center font-mono">{ath.tens}</td>
                          <td className="p-3 text-center font-mono">{ath.xs}</td>
                        </tr>
                      );
                    })}
                    {filteredAthletes.length === 0 && (
                      <tr>
                        <td colSpan={9} className="p-8 text-center text-zinc-500 font-medium">
                          Data atlet tidak ditemukan dengan filter saat ini.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              
              {/* Footer Table Info */}
              <div className="bg-zinc-900/30 border-t border-zinc-800/60 px-4 py-3 flex items-center justify-between text-[11px] text-zinc-400">
                <span>Daftar Turnamen: <strong className="text-zinc-200">{eventDetail.name}</strong></span>
                <span>Menampilkan <strong className="text-emerald-400">{filteredAthletes.length}</strong> dari <strong className="text-zinc-200">{athletes.length}</strong> total baris data kualifikasi</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
