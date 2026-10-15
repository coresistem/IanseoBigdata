import React from 'react';
import { BookOpen, Key, Terminal, Code2, AlertCircle, Sparkles, Server, Check } from 'lucide-react';

export default function Documentation() {
  return (
    <div id="documentation-root" className="bg-zinc-950 border border-zinc-800 rounded-xl p-6 text-zinc-300 font-sans space-y-6">
      
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-zinc-800 pb-4">
        <BookOpen className="w-6 h-6 text-emerald-400" />
        <div>
          <h3 className="font-semibold text-base text-zinc-100">Panduan Teknis & Arsitektur Scraper</h3>
          <p className="text-xs text-zinc-400">Dokumentasi mendalam mengenai alur kerja, logika parsing dinamis, dan penanganan PDF.</p>
        </div>
      </div>

      {/* Alur Kerja Section */}
      <section className="space-y-3">
        <h4 className="font-semibold text-sm text-zinc-200 border-l-2 border-emerald-500 pl-2">1. Penjelasan Alur Jalannya Kode</h4>
        <p className="text-xs text-zinc-400 leading-relaxed">
          Engine web scraper Ianseo ini dirancang dengan arsitektur modular untuk membagi tanggung jawab penanganan jaringan, penguraian HTML, parsing PDF, dan ekspor data secara rapi:
        </p>
        
        <div className="space-y-3 text-xs pl-2">
          <div className="flex gap-2">
            <span className="text-emerald-400 font-mono font-bold shrink-0">Step A:</span>
            <p>
              <strong>Inisialisasi & Pengaturan Sesi (<code className="text-zinc-300 font-mono">scraper_engine.py</code>)</strong>: Menyiapkan objek <code className="text-emerald-400">requests.Session()</code> untuk menjaga efisiensi koneksi (HTTP Keep-Alive). Menentukan rentang delay dinamis untuk mematuhi etika scraping, serta memuat daftar User-Agent populer.
            </p>
          </div>

          <div className="flex gap-2">
            <span className="text-emerald-400 font-mono font-bold shrink-0">Step B:</span>
            <p>
              <strong>Pencarian Turnamen Nasional (Level 1)</strong>: Fungsi <code className="text-zinc-300 font-mono">scrape_indonesian_events()</code> mengirim GET request ke halaman <code className="text-zinc-300 font-mono">TourList.php?countryid=INA</code>. HTML diurai menggunakan BeautifulSoup untuk mengekstrak baris turnamen, nama, tanggal, lokasi, serta ID unik Turnamen.
            </p>
          </div>

          <div className="flex gap-2">
            <span className="text-emerald-400 font-mono font-bold shrink-0">Step C:</span>
            <p>
              <strong>Pemetaan Tautan Menu (Level 2)</strong>: Dengan ID turnamen terpilih, program menembak halaman <code className="text-zinc-300 font-mono">Tournament.php?id=[ID]</code>. Fungsi <code className="text-emerald-400">IanseoParser.extract_event_navigation()</code> mencari tautan-tautan hasil yang bervariasi (kualifikasi, eliminasi, regu, atau PDF).
            </p>
          </div>

          <div className="flex gap-2">
            <span className="text-emerald-400 font-mono font-bold shrink-0">Step D:</span>
            <p>
              <strong>Parsing Hasil Atlet & Skor (Level 3)</strong>: Program mendatangi halaman kualifikasi (biasanya tautan <code className="text-zinc-300 font-mono">ResultList.php</code>). Di sini, fungsi <code className="text-emerald-400">parse_scores_table()</code> mengidentifikasi kolom header secara cerdas menggunakan pencocokan regex teks ("rank", "name", "club", dll.) untuk mendukung variasi kolom tabel Ianseo.
            </p>
          </div>

          <div className="flex gap-2">
            <span className="text-emerald-400 font-mono font-bold shrink-0">Step E:</span>
            <p>
              <strong>Konsolidasi ke Pandas (<code className="text-zinc-300 font-mono">data_handler.py</code>)</strong>: Seluruh dictionary data atlet dari berbagai kategori disatukan menjadi sebuah Pandas DataFrame. Tipe data kolom dikonversi ke numerik, baris diurutkan secara logis, lalu diekspor menjadi format CSV, JSON, atau Excel dengan tab multi-sheet berdasarkan kategori.
            </p>
          </div>
        </div>
      </section>

      {/* Dinamika URL Section */}
      <section className="space-y-3 pt-2">
        <h4 className="font-semibold text-sm text-zinc-200 border-l-2 border-emerald-500 pl-2">2. Menangani Struktur URL Ianseo yang Dinamis</h4>
        <p className="text-xs text-zinc-400 leading-relaxed">
          Ianseo menggunakan struktur CMS PHP tradisional di mana parameter URL sangat menentukan fungsionalitas halaman. Berikut adalah taktik yang digunakan kode Python untuk menangani dinamisme ini:
        </p>

        <ul className="list-disc pl-5 text-xs text-zinc-400 space-y-2">
          <li>
            <strong>Pembersihan URL Relatif:</strong> Ianseo seringkali merujuk file internal menggunakan path relatif seperti <code className="text-zinc-200 font-mono">ResultList.php?Reg=...</code>. Engine scraper menangani ini dengan mendeteksi jika URL tidak diawali dengan "http", lalu otomatis menggabungkannya dengan <code className="text-emerald-400">https://www.ianseo.net/</code>.
          </li>
          <li>
            <strong>Deteksi Parameter ID Fleksibel:</strong> Query string Ianseo bervariasi antara huruf besar dan kecil (misal: <code className="text-zinc-200 font-mono">?id=123</code> atau <code className="text-zinc-200 font-mono">?Id=123</code> atau <code className="text-zinc-200 font-mono">?ID=123</code>). Skrip kami mengonversi string parameter ke format huruf kecil sebelum dicocokkan demi menjamin akurasi.
          </li>
          <li>
            <strong>Fallback Dokumen PDF Resmi:</strong> Apabila event disetel tertutup oleh panitia sehingga tabel HTML tidak di-publish, satu-satunya cara adalah mengekstrak file PDF turnamen book yang biasanya tertaut dengan penamaan dinamis di folder <code className="text-zinc-200 font-mono">/TourFiles/</code>. Kode kita memetakan link PDF ini secara otomatis untuk di-download.
          </li>
        </ul>
      </section>

      {/* PDF Extraction Section */}
      <section className="space-y-3 pt-2">
        <h4 className="font-semibold text-sm text-zinc-200 border-l-2 border-emerald-500 pl-2">3. Ekstraksi Data dari Dokumen PDF (<code className="text-zinc-300 font-mono">pdfplumber</code>)</h4>
        <p className="text-xs text-zinc-400 leading-relaxed">
          Tantangan terbesar data panahan di Ianseo adalah tingginya ketergantungan panitia lokal pada dokumen PDF. File PDF tidak memiliki struktur baris/kolom HTML yang jelas, melainkan hanya koordinat teks dan garis gambar.
        </p>

        <div className="bg-zinc-900/60 border border-zinc-800 p-4 rounded-xl text-xs space-y-2 leading-relaxed">
          <p className="font-semibold text-zinc-200 flex items-center gap-1.5">
            <Sparkles className="w-4 h-4 text-amber-400" />
            Mengapa Memilih <code className="text-emerald-400">pdfplumber</code> dibanding PyPDF2?
          </p>
          <p className="text-zinc-400">
            Berbeda dengan library ekstraksi PDF biasa yang hanya menarik teks mentah berantakan secara berurutan, <code className="text-zinc-300 font-semibold">pdfplumber</code> mampu mendeteksi batas-batas visual garis tabel (gridlines) dalam PDF. Hal ini memungkinkan pemetaan koordinat baris dan kolom yang presisi, menghasilkan output berbentuk <code className="text-zinc-100 font-mono">List of Lists</code> yang sangat mudah ditransfer ke dalam baris tabel data atlet.
          </p>
          <div className="border-t border-zinc-800/80 pt-2 mt-2">
            <span className="font-semibold text-zinc-300 block mb-1">Rekomendasi Strategi Parsing PDF:</span>
            <ul className="list-decimal pl-4 space-y-1 text-zinc-400">
              <li>Lakukan download PDF ke penyimpanan lokal secara aman menggunakan chunk-streaming.</li>
              <li>Buka file dengan <code className="text-zinc-300 font-mono">pdfplumber.open(path)</code>.</li>
              <li>Gunakan metode <code className="text-emerald-400 font-mono">page.extract_tables()</code> pada halaman target.</li>
              <li>Lakukan filtering baris: Cari baris header yang mengandung istilah kunci pencarian seperti "Rank", "Athlete", atau "Club". Abaikan baris-baris kosong atau header dekoratif dokumen.</li>
            </ul>
          </div>
        </div>
      </section>

      {/* Best Practices & Ethics */}
      <section className="space-y-3 pt-2">
        <h4 className="font-semibold text-sm text-zinc-200 border-l-2 border-emerald-500 pl-2">4. Etika Scraping & Keamanan Data</h4>
        
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
          <div className="bg-zinc-950 p-3 rounded-lg border border-zinc-850">
            <span className="font-semibold text-emerald-400 block mb-1">Jeda Waktu Dinamis</span>
            Gunakan interval delay acak (1.5s - 3.5s) agar request terasa organik seperti perilaku manusia normal.
          </div>
          <div className="bg-zinc-950 p-3 rounded-lg border border-zinc-850">
            <span className="font-semibold text-emerald-400 block mb-1">Rotasi Header Sesi</span>
            Ganti browser User-Agent secara dinamis pada setiap peluncuran scraper guna menghindari pemblokiran IP oleh Cloudflare.
          </div>
          <div className="bg-zinc-950 p-3 rounded-lg border border-zinc-850">
            <span className="font-semibold text-emerald-400 block mb-1">Penyimpanan Terstruktur</span>
            Kelompokkan ekspor data dalam folder khusus <code className="text-zinc-200">output_data/</code> dan gunakan file encoding UTF-8.
          </div>
        </div>
      </section>
    </div>
  );
}
