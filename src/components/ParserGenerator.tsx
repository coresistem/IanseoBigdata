import React, { useState } from 'react';
import { Sparkles, Code, Check, Copy, HelpCircle, ArrowRight, Table, AlertCircle } from 'lucide-react';

interface HTMLTemplate {
  name: string;
  description: string;
  html: string;
  expectedPython: string;
}

const HTML_TEMPLATES: HTMLTemplate[] = [
  {
    name: "Tabel Hasil Kualifikasi (ResultList.php)",
    description: "Format baris standar tabel kualifikasi atlet dengan skor per sesi.",
    html: `<tr class="grid">
  <td class="tableVal">1</td>
  <td class="tableVal">12A</td>
  <td class="tableVal">Arif Dwi Pangestu</td>
  <td class="tableVal">DKI Jakarta (DKI)</td>
  <td class="tableVal">342</td>
  <td class="tableVal">345</td>
  <td class="tableVal fontBold">687</td>
  <td class="tableVal">41/18</td>
</tr>`,
    expectedPython: `# Kode Ekstraksi BeautifulSoup untuk baris kualifikasi ini:
cols = row.find_all("td")
if len(cols) >= 8:
    rank = cols[0].get_text(strip=True)
    back_no = cols[1].get_text(strip=True)
    athlete_name = cols[2].get_text(strip=True)
    club_provinsi = cols[3].get_text(strip=True)
    distance_1 = cols[4].get_text(strip=True)
    distance_2 = cols[5].get_text(strip=True)
    total_score = cols[6].get_text(strip=True)
    
    # Menangani kolom gabungan 10s/Xs (misal: "41/18")
    tens_xs_text = cols[7].get_text(strip=True)
    tens, xs = ("0", "0")
    if "/" in tens_xs_text:
        parts = tens_xs_text.split("/")
        tens = parts[0].strip()
        xs = parts[1].strip() if len(parts) > 1 else "0"
        
    print(f"Atlet: {athlete_name}, Skor: {total_score}, 10s: {tens}, Xs: {xs}")`
  },
  {
    name: "Baris Navigasi Event (Tournament.php)",
    description: "Format link daftar kategori hasil kualifikasi di halaman detail event.",
    html: `<div class="menuItem">
  <a href="ResultList.php?id=17290&Class=RM" class="menuLink">
    Recurve Men Individual Qualification
  </a>
</div>`,
    expectedPython: `# Kode Ekstraksi BeautifulSoup untuk mencari link kualifikasi ini:
links = soup.find_all("a")
for link in links:
    href = link.get("href", "")
    text = link.get_text(strip=True)
    if "ResultList.php" in href and "Qualification" in text:
        category = text.replace("Qualification", "").strip()
        full_url = f"https://www.ianseo.net/{href}"
        print(f"Kategori Terdeteksi: {category} -> Link: {full_url}")`
  },
  {
    name: "Link Buku Hasil PDF (Tournament.php)",
    description: "Pola link dokumen PDF buku hasil lengkap turnamen.",
    html: `<div class="docLink">
  <a href="Book.php?id=17290" target="_blank">
    <img src="images/pdf_icon.png" /> Official Results Book (PDF)
  </a>
</div>`,
    expectedPython: `# Kode Ekstraksi BeautifulSoup untuk mendeteksi link buku hasil PDF:
pdf_links = []
for link in soup.find_all("a"):
    href = link.get("href", "")
    text = link.get_text(strip=True)
    if "Book.php" in href or href.endswith(".pdf") or "PDF" in text.upper():
        full_pdf_url = f"https://www.ianseo.net/{href}"
        print(f"Dokumen PDF Ditemukan: {text} -> URL: {full_pdf_url}")`
  }
];

export default function ParserGenerator() {
  const [selectedTemplateIdx, setSelectedTemplateIdx] = useState<number>(0);
  const [customHTML, setCustomHTML] = useState<string>("");
  const [isGenerated, setIsGenerated] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);

  const activeTemplate = HTML_TEMPLATES[selectedTemplateIdx];
  const displayHTML = customHTML || activeTemplate.html;
  
  const handleSelectTemplate = (idx: number) => {
    setSelectedTemplateIdx(idx);
    setCustomHTML("");
    setIsGenerated(false);
  };

  const handleGenerate = () => {
    setIsGenerated(true);
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(activeTemplate.expectedPython);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div id="parser-generator-root" className="bg-zinc-950 border border-zinc-800 rounded-xl p-6 text-zinc-300 font-sans space-y-6">
      
      {/* Intro */}
      <div className="flex items-center gap-3 border-b border-zinc-800 pb-4">
        <Sparkles className="w-6 h-6 text-emerald-400" />
        <div>
          <h3 className="font-semibold text-base text-zinc-100">HTML Parser Generator & Helper</h3>
          <p className="text-xs text-zinc-400">Pilih template elemen HTML Ianseo untuk melatih dan melihat kode BeautifulSoup Python pendeteksi data.</p>
        </div>
      </div>

      {/* Templates Selector */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {HTML_TEMPLATES.map((tpl, idx) => {
          const isSelected = selectedTemplateIdx === idx && !customHTML;
          return (
            <button
              id={`btn-tpl-${idx}`}
              key={idx}
              onClick={() => handleSelectTemplate(idx)}
              className={`p-3 rounded-lg text-left border text-xs transition-all ${
                isSelected
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                  : 'bg-zinc-900/40 border-zinc-800 text-zinc-400 hover:bg-zinc-900/80 hover:text-zinc-200'
              }`}
            >
              <div className="font-semibold mb-1 flex items-center gap-1.5">
                <Table className="w-3.5 h-3.5" />
                {tpl.name}
              </div>
              <div className="text-[10px] text-zinc-500 leading-normal">{tpl.description}</div>
            </button>
          );
        })}
      </div>

      {/* HTML Input and Expected Python Output Column */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        
        {/* HTML Code Snippet */}
        <div className="space-y-2">
          <div className="flex justify-between items-center">
            <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Markup HTML Ianseo (Input)</span>
            {customHTML && (
              <button 
                id="btn-reset-custom-html"
                onClick={() => handleSelectTemplate(selectedTemplateIdx)}
                className="text-[10px] text-emerald-400 hover:underline"
              >
                Gunakan Template
              </button>
            )}
          </div>
          
          <div className="relative">
            <textarea
              id="html-input-textarea"
              value={displayHTML}
              onChange={(e) => {
                setCustomHTML(e.target.value);
                setIsGenerated(false);
              }}
              placeholder="Tempel potongan kode HTML Ianseo di sini..."
              className="w-full h-56 p-3 bg-zinc-950 text-zinc-300 font-mono text-xs border border-zinc-850 rounded-lg focus:outline-none focus:border-emerald-500/50 leading-relaxed scrollbar-thin select-text"
            />
          </div>
          
          <button
            id="btn-generate-parsing-code"
            onClick={handleGenerate}
            className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-200 font-semibold rounded-lg text-xs transition-all"
          >
            <Code className="w-4 h-4 text-emerald-400" />
            Buat Aturan Parser Python
          </button>
        </div>

        {/* Python Parser Output */}
        <div className="space-y-2">
          <div className="flex justify-between items-center">
            <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">BeautifulSoup Python (Output)</span>
            <button
              id="btn-copy-parser-snippet"
              onClick={handleCopy}
              className="flex items-center gap-1 text-[11px] text-emerald-400 hover:underline"
            >
              {copied ? (
                <>
                  <Check className="w-3 h-3" />
                  Tersalin!
                </>
              ) : (
                <>
                  <Copy className="w-3 h-3" />
                  Salin Kode
                </>
              )}
            </button>
          </div>

          <div className="h-68 p-4 bg-zinc-900/30 border border-zinc-800/80 rounded-lg overflow-auto font-mono text-xs leading-relaxed text-zinc-300 relative select-text">
            {isGenerated || !customHTML ? (
              <pre className="whitespace-pre overflow-x-auto text-emerald-400/90">
                {activeTemplate.expectedPython}
              </pre>
            ) : (
              <div className="h-full flex items-center justify-center flex-col gap-2 text-zinc-500 text-center px-4">
                <AlertCircle className="w-6 h-6 text-zinc-600" />
                <span className="text-xs">Klik "Buat Aturan Parser Python" untuk menganalisis dan merekonstruksi markup HTML yang Anda masukkan.</span>
              </div>
            )}
          </div>
        </div>

      </div>

      {/* Warning/Tips */}
      <div className="p-3.5 bg-zinc-900/20 rounded-lg border border-zinc-800/40 text-[11px] leading-relaxed text-zinc-400 flex gap-2">
        <HelpCircle className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold text-zinc-300">Tips Pengembang:</span> Ianseo menggunakan penataan tabel bersarang (nested tables) yang cukup rumit. Selalu gunakan pembersihan <code className="text-zinc-100 font-mono">strip=True</code> pada pemanggilan <code className="text-emerald-400">get_text()</code> BeautifulSoup untuk menghindari penimbunan spasi kosong atau karakter baris baru (\n) yang dapat merusak integritas data total skor atau peringkat.
        </div>
      </div>

    </div>
  );
}
