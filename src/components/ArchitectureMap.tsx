import React from 'react';
import { Network, Database, FileText, ChevronRight, HelpCircle, Layers, ArrowRight, ShieldCheck, Cpu } from 'lucide-react';

export default function ArchitectureMap() {
  return (
    <div id="architecture-map-root" className="bg-zinc-950 border border-zinc-800 rounded-xl p-6 text-zinc-300 font-sans space-y-8">
      {/* Introduction */}
      <div className="flex items-center gap-3 border-b border-zinc-800 pb-4">
        <Layers className="w-6 h-6 text-emerald-400" />
        <div>
          <h3 className="font-semibold text-base text-zinc-100">Arsitektur Aliran Data Ianseo Scraper</h3>
          <p className="text-xs text-zinc-400">Peta interaktif navigasi URL dinamis Ianseo dan proses ekstraksi multi-level.</p>
        </div>
      </div>

      {/* Visual Flow Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 relative">
        
        {/* Step 1: Level 1 List */}
        <div className="bg-zinc-900/40 border border-zinc-800/80 rounded-xl p-4 flex flex-col justify-between relative group hover:border-emerald-500/30 transition-colors">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[10px] bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded-full font-semibold">LEVEL 1</span>
              <Network className="w-4 h-4 text-emerald-400" />
            </div>
            <h4 className="font-semibold text-xs text-zinc-200">Daftar Turnamen (Indonesia)</h4>
            <div className="p-2 bg-zinc-950 rounded font-mono text-[10px] break-all border border-zinc-800 text-zinc-400">
              TourList.php?countryid=INA
            </div>
            <p className="text-[11px] text-zinc-400 leading-relaxed">
              Membuka katalog kompetisi nasional. Parser BS4 memindai tabel utama (<code className="text-emerald-400">class="display"</code>) untuk mengumpulkan ID Event dan detail dasar turnamen.
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-zinc-800/60 text-[10px] text-zinc-500 font-medium">
            Output: <span className="text-zinc-300">Array of Event IDs & Names</span>
          </div>
        </div>

        {/* Step 2: Level 2 Detail & Menus */}
        <div className="bg-zinc-900/40 border border-zinc-800/80 rounded-xl p-4 flex flex-col justify-between group hover:border-emerald-500/30 transition-colors">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[10px] bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded-full font-semibold">LEVEL 2</span>
              <Cpu className="w-4 h-4 text-emerald-400" />
            </div>
            <h4 className="font-semibold text-xs text-zinc-200">Navigasi Event Dinamis</h4>
            <div className="p-2 bg-zinc-950 rounded font-mono text-[10px] break-all border border-zinc-800 text-zinc-400">
              Tournament.php?id=&#123;id&#125;
            </div>
            <p className="text-[11px] text-zinc-400 leading-relaxed">
              Setiap turnamen memiliki susunan menu berbeda. Parser memindai seluruh tag <code className="text-emerald-400">&lt;a&gt;</code> untuk memetakan tautan sub-bab kualifikasi, eliminasi, dan berkas PDF.
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-zinc-800/60 text-[10px] text-zinc-500 font-medium">
            Output: <span className="text-zinc-300">Tautan Sub-Kategori Hasil</span>
          </div>
        </div>

        {/* Step 3: Level 3 Parsing HTML / PDF */}
        <div className="bg-zinc-900/40 border border-zinc-800/80 rounded-xl p-4 flex flex-col justify-between group hover:border-emerald-500/30 transition-colors col-span-1 md:col-span-2">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[10px] bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded-full font-semibold">LEVEL 3</span>
              <Database className="w-4 h-4 text-emerald-400" />
            </div>
            <h4 className="font-semibold text-xs text-zinc-200">Ekstraksi Skor & Atlet (Dual-Engine)</h4>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
              <div className="p-2.5 bg-zinc-950 rounded-lg border border-zinc-800/60 space-y-1.5">
                <span className="text-[9px] text-emerald-400 font-semibold uppercase block">Engine A: HTML Parser</span>
                <span className="font-mono text-[9px] block text-zinc-500">ResultList.php?id=...</span>
                <p className="text-[10px] text-zinc-400 leading-snug">
                  Mengekstrak tabel dengan cerdas. Melakukan auto-mapping header kolom untuk mengambil Rank, Target, Nama, Klub, dan Skor per jarak.
                </p>
              </div>

              <div className="p-2.5 bg-zinc-950 rounded-lg border border-zinc-800/60 space-y-1.5">
                <span className="text-[9px] text-yellow-500 font-semibold uppercase block">Engine B: PDF Extractor</span>
                <span className="font-mono text-[9px] block text-zinc-500">pdfplumber & urllib</span>
                <p className="text-[10px] text-zinc-400 leading-snug">
                  Mengunduh PDF Buku Hasil Turnamen. Memindai struktur dokumen menggunakan koordinat tabel untuk merekonstruksi data hasil atlet.
                </p>
              </div>
            </div>
          </div>
          
          <div className="mt-4 pt-3 border-t border-zinc-800/60 flex items-center justify-between text-[10px] text-zinc-500 font-medium">
            <span>Output: <span className="text-zinc-300">Clean Athlete Records List</span></span>
            <span className="text-emerald-500 font-mono">Pandas DataFrame</span>
          </div>
        </div>

      </div>

      {/* Advanced Challenges & How the Python Code Solves Them */}
      <div className="bg-zinc-900/20 border border-zinc-800/80 rounded-xl p-5 space-y-4">
        <h4 className="font-semibold text-xs text-zinc-200 uppercase tracking-wider flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          Penanganan Tantangan Teknis di Dalam Kode Python
        </h4>
        
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div className="space-y-2">
            <h5 className="font-semibold text-zinc-300">1. Struktur HTML Ianseo yang Tidak Konsisten</h5>
            <p className="text-zinc-400 leading-relaxed text-[11px]">
              <strong>Solusi:</strong> Kode Python menggunakan <code className="text-emerald-400">IanseoParser.parse_scores_table()</code> yang dilengkapi dengan deteksi kolom cerdas. Alih-alih melakukan hardcode index kolom, scraper memetakan isi header secara dinamis (mencari regex "rank", "pos", "athlete", "atlet", "club", "provinsi"). Ini memastikan scraping tetap bekerja walau ada penambahan atau pengurangan kolom di situs aslinya.
            </p>
          </div>

          <div className="space-y-2">
            <h5 className="font-semibold text-zinc-300">2. Keamanan Anti-Bot & Blokir IP</h5>
            <p className="text-zinc-400 leading-relaxed text-[11px]">
              <strong>Solusi:</strong> Engine ini memadukan rotasi acak User-Agent modern pada setiap request, menggunakan custom headers lengkap, dan menerapkan <code className="text-emerald-400">random.uniform()</code> delay antara request. Hal ini meminimalkan deteksi bot dan memastikan scraper berjalan secara etis tanpa membebani server Ianseo.
            </p>
          </div>

          <div className="space-y-2">
            <h5 className="font-semibold text-zinc-300">3. Hasil Pertandingan yang Hanya Berbentuk PDF</h5>
            <p className="text-zinc-400 leading-relaxed text-[11px]">
              <strong>Solusi:</strong> Menyediakan modul <code className="text-emerald-400">pdf_parser.py</code> yang memanfaatkan library canggih <code className="text-zinc-300">pdfplumber</code>. Modul ini secara dinamis mengunduh file PDF Buku Hasil, memindai halaman demi halaman, menyaring baris non-hasil, serta mengonversi tabel PDF menjadi baris dictionary data atlet yang kompatibel dengan DataFrame utama.
            </p>
          </div>

          <div className="space-y-2">
            <h5 className="font-semibold text-zinc-300">4. Ekspor Data Kompleks ke Excel</h5>
            <p className="text-zinc-400 leading-relaxed text-[11px]">
              <strong>Solusi:</strong> Menggunakan <code className="text-emerald-400">pd.ExcelWriter()</code> berbasis <code className="text-zinc-300">openpyxl</code> untuk memilah data. Selain lembar kerja (Sheet) utama berisi seluruh hasil kualifikasi gabungan, program otomatis memisahkan data ke sheet-sheet terpisah berdasarkan kategori (Recurve Men, Compound, Barebow, dll), sehingga siap disajikan langsung kepada analis data.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
