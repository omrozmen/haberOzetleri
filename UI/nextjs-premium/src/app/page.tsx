"use client";

import { useState, useEffect, useMemo } from "react";
import {
  Search,
  Clock,
  ExternalLink,
  X,
  Globe,
  Bell,
  ArrowRight,
  Bookmark
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

interface NewsEntry {
  title: string;
  url: string;
  summary: string;
  source: string;
  model: string;
}

const API_BASE = "http://127.0.0.1:5000";

export default function Home() {
  const [sources, setSources] = useState<string[]>([]);
  const [selectedSource, setSelectedSource] = useState<string>("");
  const [entries, setEntries] = useState<NewsEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedNews, setSelectedNews] = useState<NewsEntry | null>(null);

  // Fetch sources
  useEffect(() => {
    const fetchSources = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/sources`);
        const data = await res.json();
        if (data.sources) {
          setSources(data.sources);
          if (data.sources.length > 0) setSelectedSource(data.sources[0]);
        }
      } catch (err) {
        console.error("Failed to fetch sources", err);
        setError("Veri bağlantısı sağlanamadı.");
      }
    };
    fetchSources();
  }, []);

  // Fetch entries
  useEffect(() => {
    if (!selectedSource) return;

    const fetchEntries = async () => {
      setLoading(true);
      try {
        const res = await fetch(`${API_BASE}/api/entries?source=${selectedSource}&limit=40`);
        const data = await res.json();
        setEntries(data.entries || []);
      } catch (err) {
        console.error("Failed to fetch entries", err);
      } finally {
        setLoading(false);
      }
    };
    fetchEntries();
  }, [selectedSource]);

  // Client-side search
  const filteredEntries = useMemo(() => {
    if (!searchTerm.trim()) return entries;
    const term = searchTerm.toLowerCase();
    return entries.filter(e =>
      e.title.toLowerCase().includes(term) ||
      (e.summary && e.summary.toLowerCase().includes(term))
    );
  }, [entries, searchTerm]);

  return (
    <div className="flex h-screen bg-[#010409] text-slate-100 overflow-hidden font-inter selection:bg-blue-500/30 selection:text-white">

      {/* Subtle Background Glows */}
      <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-blue-600/5 rounded-full blur-[120px] pointer-events-none -mr-40 -mt-20" />
      <div className="absolute bottom-0 left-0 w-[500px] h-[500px] bg-emerald-600/5 rounded-full blur-[100px] pointer-events-none -ml-40 -mb-20" />

      {/* Side Navigation - Refined */}
      <aside className="w-72 bg-[#010409] border-r border-white-[0.05] flex flex-col z-20 shadow-2xl">
        <div className="p-8 pb-12">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-blue-400 flex items-center justify-center shadow-lg shadow-blue-500/10">
              <Globe className="w-4 h-4 text-white" />
            </div>
            <h1 className="text-lg font-black tracking-tight text-white uppercase">
              News<span className="text-blue-500">Hub</span>
            </h1>
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto px-4 py-2 space-y-1 custom-scrollbar">
          <p className="px-5 text-[10px] font-bold text-slate-600 uppercase tracking-widest mb-6">
            Kategoriler
          </p>
          {sources.map(source => (
            <button
              key={source}
              onClick={() => setSelectedSource(source)}
              className={cn(
                "w-full flex items-center gap-4 px-5 py-3.5 rounded-xl transition-all duration-200 group relative",
                selectedSource === source
                  ? "bg-slate-900/50 text-white border border-white/5 shadow-sm"
                  : "text-slate-500 hover:text-slate-200 hover:bg-white-[0.02]"
              )}
            >
              <div className={cn(
                "w-1.5 h-1.5 rounded-full transition-all",
                selectedSource === source ? "bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.6)]" : "bg-slate-800"
              )} />
              <span className="text-sm font-bold capitalize truncate">
                {source.replace(/_/g, ' ')}
              </span>
              {selectedSource === source && (
                <div className="absolute right-4 w-1 h-4 bg-blue-500 rounded-full" />
              )}
            </button>
          ))}
        </nav>

        <div className="p-6">
          <div className="p-4 rounded-2xl bg-slate-900/30 border border-white/5 text-center">
            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">v2.1 Premium Portal</p>
          </div>
        </div>
      </aside>

      {/* Main Container */}
      <main className="flex-1 flex flex-col min-w-0 z-10">
        {/* Header - Clean & Minimal */}
        <header className="h-24 bg-[#010409]/80 backdrop-blur-xl border-b border-white-[0.05] flex items-center justify-between px-10 shrink-0">
          <div className="flex items-center gap-10 flex-1">
            <h2 className="text-2xl font-black text-white tracking-tight capitalize">
              {selectedSource.replace(/_/g, ' ')}
              <span className="text-slate-700 ml-2 font-light">/ Güncel</span>
            </h2>

            <div className="relative max-w-md w-full group">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 group-focus-within:text-blue-500 transition-colors" />
              <input
                type="text"
                placeholder="Ara..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full bg-[#0d1117] border border-white/5 focus:border-blue-500/20 rounded-xl py-2.5 pl-11 pr-5 text-sm font-medium placeholder:text-slate-600 focus:outline-none transition-all"
              />
            </div>
          </div>

          <div className="flex items-center gap-6">
            <button className="text-slate-500 hover:text-white transition-colors">
              <Bell className="w-5 h-5" />
            </button>
            <div className="w-px h-6 bg-white/5" />
            <div className="flex items-center gap-2 group cursor-pointer">
              <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-[10px] font-bold">EH</div>
            </div>
          </div>
        </header>

        {error && (
          <div className="mx-10 mt-6 rounded-2xl border border-red-500/20 bg-red-500/5 px-6 py-4 text-sm text-red-200">
            {error}
          </div>
        )}

        {/* Content Feed */}
        <div className="flex-1 overflow-y-auto px-10 py-10 custom-scrollbar">
          <div className="max-w-6xl mx-auto">
            {loading && entries.length === 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {[...Array(6)].map((_, i) => (
                  <div key={i} className="h-72 rounded-3xl bg-white/5 animate-pulse border border-white/5" />
                ))}
              </div>
            ) : (
              <AnimatePresence mode="popLayout">
                <motion.div
                  layout
                  className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
                >
                  {filteredEntries.map((entry, idx) => (
                    <motion.article
                      initial={{ opacity: 0, scale: 0.98 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: idx * 0.03 }}
                      key={entry.title + idx}
                      onClick={() => setSelectedNews(entry)}
                      className="group bg-[#0d1117]/50 border border-white/5 rounded-[28px] p-8 cursor-pointer hover:bg-[#0d1117] hover:border-blue-500/20 hover:shadow-2xl hover:shadow-blue-500/5 transition-all duration-300 flex flex-col overflow-hidden relative"
                    >
                      <div className="flex items-center justify-between mb-6">
                        <span className={cn(
                          "px-2.5 py-1 rounded-lg text-[9px] font-bold uppercase tracking-widest",
                          idx % 3 === 0 ? "bg-blue-500/10 text-blue-400" :
                            idx % 3 === 1 ? "bg-amber-500/10 text-amber-400" :
                              "bg-emerald-500/10 text-emerald-400"
                        )}>
                          {selectedSource}
                        </span>
                        <span className="text-[9px] font-bold text-slate-600 uppercase tracking-widest flex items-center gap-1.5">
                          <Clock className="w-3 h-3" /> Son Dakika
                        </span>
                      </div>

                      <h3 className="text-lg font-bold text-white leading-snug mb-5 group-hover:text-blue-400 transition-colors line-clamp-3">
                        {entry.title}
                      </h3>

                      <p className="text-slate-500 text-sm leading-relaxed line-clamp-3 font-medium opacity-80 group-hover:opacity-100 transition-opacity">
                        {entry.summary || "Haber detayı için tıklayınız."}
                      </p>

                      <div className="mt-8 flex items-center justify-between border-t border-white/5 pt-6">
                        <span className="text-[10px] font-bold text-slate-600 group-hover:text-slate-300 uppercase tracking-wider transition-colors">
                          Detayları İncele
                        </span>
                        <div className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center group-hover:bg-blue-500 transition-all duration-300">
                          <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-white" />
                        </div>
                      </div>
                    </motion.article>
                  ))}
                </motion.div>
              </AnimatePresence>
            )}
          </div>
        </div>
      </main>

      {/* COMPACT MODAL DESIGN */}
      <AnimatePresence>
        {selectedNews && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-6">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setSelectedNews(null)}
              className="absolute inset-0 bg-black/80 backdrop-blur-md"
            />

            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="relative w-full max-w-3xl bg-[#0d1117] border border-white/10 rounded-[32px] overflow-hidden flex flex-col shadow-[0_32px_128px_rgba(0,0,0,0.8)]"
            >
              {/* Header */}
              <div className="px-10 h-20 flex items-center justify-between border-b border-white/5 bg-white-[0.01]">
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-blue-500" />
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em]">{selectedSource} Haber Özeti</span>
                </div>
                <button
                  onClick={() => setSelectedNews(null)}
                  className="w-10 h-10 flex items-center justify-center rounded-xl bg-white/5 hover:bg-red-500/10 hover:text-red-500 transition-all"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Body */}
              <div className="flex-1 overflow-y-auto px-10 py-12 custom-scrollbar">
                <div className="flex items-center gap-2 mb-6">
                  <Clock className="w-3.5 h-3.5 text-slate-600" />
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Az Önce Paylaşıldı</span>
                </div>

                <h2 className="text-3xl font-black text-white leading-[1.2] mb-10 tracking-tight">
                  {selectedNews.title}
                </h2>

                <div className="p-8 rounded-3xl bg-blue-500/5 border border-blue-500/10 relative group">
                  <p className="text-slate-300 text-lg leading-relaxed font-medium">
                    {selectedNews.summary || "Habere dair bir özet bilgi bulunmamaktadır."}
                  </p>
                </div>

                <div className="mt-12 flex flex-col md:flex-row items-center gap-4">
                  <a
                    href={selectedNews.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="w-full md:w-auto px-8 py-4 bg-blue-600 text-white text-xs font-bold uppercase tracking-widest rounded-2xl hover:bg-blue-500 transition-all text-center flex items-center justify-center gap-2 group/btn"
                  >
                    Haberin Tamamı <ExternalLink className="w-3.5 h-3.5 group-hover/btn:scale-110 transition-transform" />
                  </a>
                  <button className="flex items-center gap-2 px-6 py-4 rounded-2xl bg-white/5 text-slate-400 hover:text-white transition-all text-xs font-bold uppercase tracking-widest">
                    <Bookmark className="w-4 h-4" /> Haberi Kaydet
                  </button>
                </div>
              </div>

              {/* Footer */}
              <div className="px-10 h-16 border-t border-white/5 bg-white-[0.01] flex items-center">
                <p className="text-[9px] font-bold text-slate-700 uppercase tracking-widest">Kaynak Linki: {selectedNews.url.split('/')[2]}</p>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
