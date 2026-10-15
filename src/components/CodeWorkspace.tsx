import React, { useState } from 'react';
import { pythonCodebase, PythonFile } from '../data/pythonCodebase';
import { FileCode, Copy, Check, Download, Search, Terminal, ChevronRight, FileText } from 'lucide-react';

export default function CodeWorkspace() {
  const [selectedFile, setSelectedFile] = useState<PythonFile>(pythonCodebase[2]); // Default scraper_engine.py
  const [searchTerm, setSearchTerm] = useState('');
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(selectedFile.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const element = document.createElement("a");
    const file = new Blob([selectedFile.content], {type: 'text/plain'});
    element.href = URL.createObjectURL(file);
    element.download = selectedFile.name;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  const filteredFiles = pythonCodebase.filter(f => 
    f.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    f.description.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div id="code-workspace-container" className="flex flex-col lg:flex-row h-full min-h-[600px] border border-zinc-800 rounded-xl overflow-hidden bg-zinc-950 font-sans text-zinc-300">
      {/* File Sidebar */}
      <div id="code-sidebar" className="w-full lg:w-72 border-r border-zinc-800 bg-zinc-900/50 p-4 flex flex-col shrink-0">
        <div className="flex items-center gap-2 mb-4">
          <Terminal className="w-5 h-5 text-emerald-400" />
          <span className="font-semibold text-zinc-100 text-sm tracking-wide uppercase">Workspace Files</span>
        </div>

        {/* Search Files */}
        <div className="relative mb-4">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-zinc-500" />
          <input
            id="file-search-input"
            type="text"
            placeholder="Cari file..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-xs bg-zinc-900 border border-zinc-800 rounded-lg text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-emerald-500/50 transition-colors"
          />
        </div>

        {/* File List */}
        <div id="sidebar-file-list" className="space-y-1 overflow-y-auto flex-1 max-h-[250px] lg:max-h-none">
          {filteredFiles.map((file) => {
            const isSelected = selectedFile.name === file.name;
            const isPython = file.language === 'python';
            
            return (
              <button
                id={`btn-file-${file.name.replace('.', '-')}`}
                key={file.name}
                onClick={() => setSelectedFile(file)}
                className={`w-full flex items-start gap-3 p-2.5 rounded-lg text-left transition-all ${
                  isSelected 
                    ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-400' 
                    : 'border border-transparent text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200'
                }`}
              >
                {isPython ? (
                  <FileCode className={`w-4 h-4 mt-0.5 shrink-0 ${isSelected ? 'text-emerald-400' : 'text-zinc-500'}`} />
                ) : (
                  <FileText className={`w-4 h-4 mt-0.5 shrink-0 ${isSelected ? 'text-emerald-400' : 'text-zinc-500'}`} />
                )}
                <div className="min-w-0">
                  <div className="text-xs font-mono font-medium truncate">{file.name}</div>
                  <div className="text-[10px] text-zinc-500 truncate mt-0.5">{file.description}</div>
                </div>
              </button>
            );
          })}
          {filteredFiles.length === 0 && (
            <div className="text-center py-6 text-xs text-zinc-500">File tidak ditemukan.</div>
          )}
        </div>

        {/* Python Environment note */}
        <div className="mt-4 pt-4 border-t border-zinc-800/80 hidden lg:block">
          <div className="bg-zinc-950/80 p-3 rounded-lg border border-zinc-800 text-[11px] leading-relaxed">
            <span className="text-emerald-400 font-semibold block mb-1">💡 Tips Python</span>
            Gunakan Python 3.8+ untuk menjalankan engine ini. Jalankan <code className="text-zinc-100 bg-zinc-900 px-1 rounded font-mono">pip install -r requirements.txt</code> sebelum memulai.
          </div>
        </div>
      </div>

      {/* Code Editor Screen */}
      <div id="code-editor" className="flex-1 flex flex-col bg-zinc-950 min-w-0">
        {/* Editor Toolbar */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800 bg-zinc-900/20">
          <div className="flex items-center gap-2 min-w-0">
            <FileCode className="w-4 h-4 text-emerald-400" />
            <span className="text-xs font-mono text-zinc-300 font-medium truncate">{selectedFile.name}</span>
            <span className="text-[10px] bg-zinc-800 text-zinc-400 px-1.5 py-0.5 rounded uppercase">{selectedFile.language}</span>
          </div>

          <div className="flex items-center gap-2">
            <button
              id="btn-copy-code"
              onClick={handleCopy}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 transition-colors"
              title="Copy Code"
            >
              {copied ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="text-emerald-400">Tersalin</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  <span>Salin</span>
                </>
              )}
            </button>

            <button
              id="btn-download-file"
              onClick={handleDownload}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium transition-colors"
              title="Download File"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Unduh</span>
            </button>
          </div>
        </div>

        {/* Code Content View */}
        <div className="flex-1 overflow-auto p-4 font-mono text-xs leading-relaxed bg-zinc-950 max-h-[500px] lg:max-h-[650px] relative select-text">
          <pre className="whitespace-pre overflow-x-auto text-zinc-300 scrollbar-thin">
            {selectedFile.content}
          </pre>
        </div>
      </div>
    </div>
  );
}
