import React, { useState } from 'react';
import { Terminal, Calendar, Clock, Globe, ChevronRight, Search, Filter, Download, Play, Check, X, Loader2 } from 'lucide-react';

interface Tournament {
  id: string;
  name: string;
  date: string;
  location: string;
}

interface DataField {
  id: string;
  name: string;
  selected: boolean;
}

type WorkflowStep = 'year' | 'tournaments' | 'selection' | 'scraping' | 'results';

export default function App() {
  const [currentStep, setCurrentStep] = useState<WorkflowStep>('year');
  const [selectedYear, setSelectedYear] = useState<string>('');
  const [selectedTournament, setSelectedTournament] = useState<Tournament | null>(null);
  const [isScraping, setIsScraping] = useState(false);
  const [scrapingProgress, setScrapingProgress] = useState(0);
  
  // Mock tournament data by year
  const tournamentsByYear: Record<string, Tournament[]> = {
    '2018': [
      { id: '15123', name: 'Kejuaraan Nasional Panahan 2018', date: '2018-04-10', location: 'Jakarta' },
      { id: '15245', name: 'PON 2018 - Cabor Panahan', date: '2018-09-15', location: 'Palembang' },
      { id: '15367', name: 'Indonesia Open Archery 2018', date: '2018-06-20', location: 'Jakarta' },
    ],
    '2019': [
      { id: '16123', name: 'Kejuaraan Nasional Panahan 2019', date: '2019-03-12', location: 'Surabaya' },
      { id: '16245', name: 'SEA Games 2019 - Panahan', date: '2019-12-05', location: 'Manila' },
      { id: '16367', name: 'Indonesia Open Archery 2019', date: '2019-07-18', location: 'Bandung' },
    ],
    '2020': [
      { id: '17123', name: 'Kejuaraan Nasional Panahan 2020', date: '2020-02-15', location: 'Yogyakarta' },
      { id: '17245', name: 'Turnamen Virtual Panahan 2020', date: '2020-08-20', location: 'Online' },
    ],
    '2021': [
      { id: '18123', name: 'Kejuaraan Nasional Panahan 2021', date: '2021-04-08', location: 'Jakarta' },
      { id: '18245', name: 'PON Papua 2021 - Panahan', date: '2021-10-12', location: 'Papua' },
      { id: '18367', name: 'Indonesia Open Archery 2021', date: '2021-06-25', location: 'Surabaya' },
    ],
    '2022': [
      { id: '19123', name: 'Kejuaraan Nasional Panahan 2022', date: '2022-03-20', location: 'Bandung' },
      { id: '19245', name: 'ASEAN Archery Championship 2022', date: '2022-11-15', location: 'Bangkok' },
      { id: '19367', name: 'Indonesia Open Archery 2022', date: '2022-07-10', location: 'Jakarta' },
    ],
    '2023': [
      { id: '20123', name: 'Kejuaraan Nasional Panahan 2023', date: '2023-04-05', location: 'Semarang' },
      { id: '20245', name: 'SEA Games 2023 - Panahan', date: '2023-05-18', location: 'Phnom Penh' },
      { id: '20367', name: 'Indonesia Open Archery 2023', date: '2023-08-22', location: 'Yogyakarta' },
    ],
    '2024': [
      { id: '21123', name: 'Kejuaraan Nasional Panahan 2024', date: '2024-03-15', location: 'Jakarta' },
      { id: '21245', name: 'Olympic Qualifier 2024', date: '2024-06-10', location: 'Surabaya' },
      { id: '21367', name: 'Indonesia Open Archery 2024', date: '2024-09-20', location: 'Bandung' },
    ],
    '2025': [
      { id: '22123', name: 'Kejuaraan Nasional Panahan 2025', date: '2025-04-12', location: 'Medan' },
      { id: '22245', name: 'World Archery Championship 2025', date: '2025-08-15', location: 'Jakarta' },
      { id: '22367', name: 'Indonesia Open Archery 2025', date: '2025-10-25', location: 'Surabaya' },
    ],
    '2026': [
      { id: '17290', name: 'Kejuaraan Nasional Panahan 2026', date: '2026-03-15', location: 'Jakarta' },
      { id: '18102', name: 'Pekan Olahraga Nasional 2026', date: '2026-09-01', location: 'Surabaya' },
      { id: '18456', name: 'Indonesia Open Archery 2026', date: '2026-05-20', location: 'Bandung' },
      { id: '18903', name: 'Kejuaraan Provinsi Jawa Barat', date: '2026-02-10', location: 'Bogor' },
      { id: '19215', name: 'Turnamen Panahan Piala Presiden', date: '2026-08-15', location: 'Yogyakarta' },
    ],
  };

  const [tournaments, setTournaments] = useState<Tournament[]>([]);

  // Data fields for selection
  const [dataFields, setDataFields] = useState<DataField[]>([
    { id: 'rank', name: 'Rank/Position', selected: true },
    { id: 'back_no', name: 'Back No/Target', selected: true },
    { id: 'athlete_name', name: 'Athlete Name', selected: true },
    { id: 'club', name: 'Club/Province', selected: true },
    { id: 'distance_1', name: 'Distance 1 Score', selected: true },
    { id: 'distance_2', name: 'Distance 2 Score', selected: true },
    { id: 'total_score', name: 'Total Score', selected: true },
    { id: 'tens', name: '10s Count', selected: true },
    { id: 'xs', name: 'Xs Count', selected: true },
    { id: 'category', name: 'Category/Division', selected: true },
  ]);

  const years = Array.from({ length: 2026 - 2018 + 1 }, (_, i) => (2018 + i).toString());

  const handleYearSelect = (year: string) => {
    setSelectedYear(year);
    setTournaments(tournamentsByYear[year] || []);
    setCurrentStep('tournaments');
  };

  const handleTournamentSelect = (tournament: Tournament) => {
    setSelectedTournament(tournament);
    setCurrentStep('selection');
  };

  const handleDataFieldToggle = (fieldId: string) => {
    setDataFields(prev => prev.map(field => 
      field.id === fieldId ? { ...field, selected: !field.selected } : field
    ));
  };

  const handleStartScraping = () => {
    setCurrentStep('scraping');
    setIsScraping(true);
    setScrapingProgress(0);
    
    // Simulate scraping progress
    const interval = setInterval(() => {
      setScrapingProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval);
          setIsScraping(false);
          setCurrentStep('results');
          return 100;
        }
        return prev + 10;
      });
    }, 500);
  };

  const handleReset = () => {
    setCurrentStep('year');
    setSelectedYear('');
    setSelectedTournament(null);
    setIsScraping(false);
    setScrapingProgress(0);
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col selection:bg-emerald-500/30 selection:text-emerald-300">
      
      {/* Header */}
      <header className="border-b border-zinc-900 bg-zinc-950 sticky top-0 z-50 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-emerald-500/10 border border-emerald-500/20 rounded-xl">
              <Terminal className="w-6 h-6 text-emerald-400" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-zinc-100">Ianseo Archery Scraper</h1>
              <p className="text-xs text-zinc-500">Data Extraction Tool</p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-xs text-zinc-400">
            <Globe className="w-4 h-4 text-emerald-500" />
            <span>ianseo.net</span>
          </div>
        </div>
      </header>

      {/* Progress Steps */}
      <div className="border-b border-zinc-900 bg-zinc-950/50">
        <div className="max-w-7xl mx-auto px-4 py-3 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            {[
              { step: 'year', label: 'Pilih Tahun' },
              { step: 'tournaments', label: 'Pilih Turnamen' },
              { step: 'selection', label: 'Pilih Data' },
              { step: 'scraping', label: 'Scraping' },
              { step: 'results', label: 'Hasil' },
            ].map((item, index) => (
              <div key={item.step} className="flex items-center flex-1">
                <div className="flex flex-col items-center flex-1">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
                    currentStep === item.step 
                      ? 'bg-emerald-500 text-white' 
                      : ['year', 'tournaments', 'selection', 'scraping', 'results'].indexOf(currentStep) > index
                      ? 'bg-emerald-500/20 text-emerald-400'
                      : 'bg-zinc-800 text-zinc-500'
                  }`}>
                    {['year', 'tournaments', 'selection', 'scraping', 'results'].indexOf(currentStep) > index ? (
                      <Check className="w-4 h-4" />
                    ) : (
                      index + 1
                    )}
                  </div>
                  <span className={`text-[10px] mt-1 ${
                    currentStep === item.step ? 'text-emerald-400' : 'text-zinc-500'
                  }`}>
                    {item.label}
                  </span>
                </div>
                {index < 4 && (
                  <ChevronRight className={`w-4 h-4 ${
                    ['year', 'tournaments', 'selection', 'scraping', 'results'].indexOf(currentStep) > index 
                      ? 'text-emerald-500' 
                      : 'text-zinc-700'
                  }`} />
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="flex-grow max-w-7xl w-full mx-auto px-4 py-8 sm:px-6 lg:px-8">
        
        {/* Step 1: Year Selection */}
        {currentStep === 'year' && (
          <div className="max-w-2xl mx-auto">
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold text-zinc-100 mb-2">Pilih Tahun Turnamen</h2>
              <p className="text-zinc-400 text-sm">Pilih tahun untuk melihat daftar turnamen yang tersedia</p>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              {years.map(year => (
                <button
                  key={year}
                  onClick={() => handleYearSelect(year)}
                  className="p-6 bg-zinc-900 border border-zinc-800 rounded-xl hover:border-emerald-500/50 hover:bg-zinc-800 transition-all group"
                >
                  <Calendar className="w-8 h-8 text-zinc-500 group-hover:text-emerald-400 mx-auto mb-3" />
                  <div className="text-lg font-bold text-zinc-100">{year}</div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Step 2: Tournament List */}
        {currentStep === 'tournaments' && (
          <div>
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-xl font-bold text-zinc-100">Daftar Turnamen {selectedYear}</h2>
                <p className="text-zinc-400 text-sm">Pilih turnamen yang ingin di-scrape</p>
              </div>
              <button
                onClick={() => setCurrentStep('year')}
                className="text-sm text-zinc-400 hover:text-zinc-200"
              >
                ← Kembali
              </button>
            </div>
            
            <div className="space-y-3">
              {tournaments.map(tournament => (
                <div
                  key={tournament.id}
                  onClick={() => handleTournamentSelect(tournament)}
                  className="p-4 bg-zinc-900 border border-zinc-800 rounded-xl hover:border-emerald-500/50 hover:bg-zinc-800 cursor-pointer transition-all"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h3 className="font-semibold text-zinc-100 mb-1">{tournament.name}</h3>
                      <div className="flex items-center gap-4 text-xs text-zinc-400">
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          {tournament.date}
                        </span>
                        <span className="flex items-center gap-1">
                          <Globe className="w-3 h-3" />
                          {tournament.location}
                        </span>
                      </div>
                    </div>
                    <ChevronRight className="w-5 h-5 text-zinc-500" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Step 3: Data Field Selection */}
        {currentStep === 'selection' && selectedTournament && (
          <div>
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-xl font-bold text-zinc-100">Pilih Data yang Akan Diambil</h2>
                <p className="text-zinc-400 text-sm">{selectedTournament.name}</p>
              </div>
              <button
                onClick={() => setCurrentStep('tournaments')}
                className="text-sm text-zinc-400 hover:text-zinc-200"
              >
                ← Kembali
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mb-6">
              {dataFields.map(field => (
                <button
                  key={field.id}
                  onClick={() => handleDataFieldToggle(field.id)}
                  className={`p-4 border rounded-xl transition-all flex items-center gap-3 ${
                    field.selected 
                      ? 'bg-emerald-500/10 border-emerald-500/30' 
                      : 'bg-zinc-900 border-zinc-800 hover:border-zinc-700'
                  }`}
                >
                  <div className={`w-5 h-5 rounded border flex items-center justify-center ${
                    field.selected 
                      ? 'bg-emerald-500 border-emerald-500' 
                      : 'border-zinc-600'
                  }`}>
                    {field.selected && <Check className="w-3 h-3 text-white" />}
                  </div>
                  <span className="text-sm text-zinc-200">{field.name}</span>
                </button>
              ))}
            </div>

            <div className="flex justify-end">
              <button
                onClick={handleStartScraping}
                className="flex items-center gap-2 px-6 py-3 bg-emerald-500 hover:bg-emerald-600 text-white font-semibold rounded-xl transition-all"
              >
                <Play className="w-4 h-4" />
                Mulai Scraping
              </button>
            </div>
          </div>
        )}

        {/* Step 4: Scraping Progress */}
        {currentStep === 'scraping' && (
          <div className="max-w-2xl mx-auto text-center">
            <div className="mb-8">
              <Loader2 className="w-16 h-16 text-emerald-500 animate-spin mx-auto mb-4" />
              <h2 className="text-2xl font-bold text-zinc-100 mb-2">Sedang Scraping...</h2>
              <p className="text-zinc-400 text-sm">Mengambil data dari {selectedTournament?.name}</p>
            </div>
            
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm text-zinc-400">Progress</span>
                <span className="text-sm font-bold text-emerald-400">{scrapingProgress}%</span>
              </div>
              <div className="w-full bg-zinc-800 rounded-full h-2">
                <div 
                  className="bg-emerald-500 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${scrapingProgress}%` }}
                />
              </div>
            </div>
          </div>
        )}

        {/* Step 5: Results */}
        {currentStep === 'results' && (
          <div>
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-xl font-bold text-zinc-100">Scraping Selesai!</h2>
                <p className="text-zinc-400 text-sm">Data berhasil diekstrak dari {selectedTournament?.name}</p>
              </div>
              <button
                onClick={handleReset}
                className="text-sm text-zinc-400 hover:text-zinc-200"
              >
                Mulai Baru
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
              <div className="p-4 bg-zinc-900 border border-zinc-800 rounded-xl">
                <div className="text-2xl font-bold text-emerald-400">156</div>
                <div className="text-xs text-zinc-400">Atlet Diekstrak</div>
              </div>
              <div className="p-4 bg-zinc-900 border border-zinc-800 rounded-xl">
                <div className="text-2xl font-bold text-emerald-400">8</div>
                <div className="text-xs text-zinc-400">Kategori</div>
              </div>
              <div className="p-4 bg-zinc-900 border border-zinc-800 rounded-xl">
                <div className="text-2xl font-bold text-emerald-400">3</div>
                <div className="text-xs text-zinc-400">Format Export</div>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <button className="flex items-center justify-center gap-2 p-4 bg-zinc-900 border border-zinc-800 rounded-xl hover:border-emerald-500/50 transition-all">
                <Download className="w-4 h-4 text-emerald-400" />
                <span className="text-sm text-zinc-200">Download CSV</span>
              </button>
              <button className="flex items-center justify-center gap-2 p-4 bg-zinc-900 border border-zinc-800 rounded-xl hover:border-emerald-500/50 transition-all">
                <Download className="w-4 h-4 text-emerald-400" />
                <span className="text-sm text-zinc-200">Download Excel</span>
              </button>
              <button className="flex items-center justify-center gap-2 p-4 bg-zinc-900 border border-zinc-800 rounded-xl hover:border-emerald-500/50 transition-all">
                <Download className="w-4 h-4 text-emerald-400" />
                <span className="text-sm text-zinc-200">Download JSON</span>
              </button>
            </div>
          </div>
        )}

      </main>

      {/* Footer */}
      <footer className="border-t border-zinc-900 bg-zinc-950 py-6 text-center text-xs text-zinc-500">
        <p>Ianseo Archery Scraper • 2026</p>
      </footer>

    </div>
  );
}
