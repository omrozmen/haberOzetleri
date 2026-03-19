import { useEffect, useRef, useState } from "react";
import { API_BASE_URL, type ModelType } from "./config";
import { SourceSelector } from "./components/SourceSelector";
import { NewsCard } from "./components/NewsCard";
import { ThemeToggle } from "./components/ThemeToggle";
import { ViewToggle } from "./components/ViewToggle";
import type { NewsEntry } from "./types";

type Theme = "light" | "dark";
type ViewMode = "grid" | "list";
const PAGE_SIZE = 5;

export default function App() {
  const model: ModelType = "llama";
  const [sources, setSources] = useState<string[]>([]);
  const [selectedSource, setSelectedSource] = useState<string | null>(null);
  const [entries, setEntries] = useState<NewsEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [theme, setTheme] = useState<Theme>("light");
  const [viewMode, setViewMode] = useState<ViewMode>("grid");
  const [visibleCount, setVisibleCount] = useState(0);
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  // Tema tercihlerini oku/yaz
  useEffect(() => {
    const saved = window.localStorage.getItem("news-ui-theme");
    if (saved === "dark" || saved === "light") {
      setTheme(saved);
    }
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    window.localStorage.setItem("news-ui-theme", theme);
  }, [theme]);

  // Model değiştiğinde kaynakları yükle
  useEffect(() => {
    let isMounted = true;
    const controller = new AbortController();

    async function fetchSources() {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(
          `${API_BASE_URL}/api/sources?model=${model}`,
          { signal: controller.signal }
        );
        if (!response.ok) {
          throw new Error("Kaynak listesi alınamadı.");
        }
        const data: { sources: string[] } = await response.json();
        if (!isMounted) return;

        setSources(data.sources);
        setSelectedSource((current) => {
          if (current && data.sources.includes(current)) {
            return current;
          }
          return data.sources[0] ?? null;
        });
      } catch (err) {
        if ((err as Error).name === "AbortError") return;
        if (isMounted) {
          setSources([]);
          setSelectedSource(null);
          setError((err as Error).message);
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    fetchSources();
    return () => {
      isMounted = false;
      controller.abort();
    };
  }, [model]);

  // Kaynak seçildiğinde haberleri getir
  useEffect(() => {
    if (!selectedSource) {
      setEntries([]);
      return;
    }

    let isMounted = true;
    const controller = new AbortController();

    async function fetchEntries() {
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams({
          model,
          source: selectedSource
        });
        const response = await fetch(
          `${API_BASE_URL}/api/entries?${params}`,
          { signal: controller.signal }
        );
        if (!response.ok) {
          throw new Error("Haberler alınamadı.");
        }
        const data: { entries: NewsEntry[] } = await response.json();
        if (!isMounted) return;
        setEntries(data.entries);
      } catch (err) {
        if ((err as Error).name === "AbortError") return;
        if (isMounted) {
          setEntries([]);
          setError((err as Error).message);
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    fetchEntries();
    return () => {
      isMounted = false;
      controller.abort();
    };
  }, [model, selectedSource]);

  useEffect(() => {
    if (!entries.length) {
      setVisibleCount(0);
      return;
    }
    setVisibleCount(Math.min(PAGE_SIZE, entries.length));
  }, [entries]);

  useEffect(() => {
    const node = sentinelRef.current;
    if (!node) return;
    if (loading) return;
    if (visibleCount >= entries.length) return;

    const observer = new IntersectionObserver(
      (entriesList) => {
        const entry = entriesList[0];
        if (entry.isIntersecting) {
          setVisibleCount((prev) => Math.min(prev + PAGE_SIZE, entries.length));
        }
      },
      { rootMargin: "200px" }
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [entries.length, loading, visibleCount]);

  const visibleEntries = entries.slice(0, visibleCount);
  const hasMoreEntries = visibleCount < entries.length;

  return (
    <div className="app">
      <ThemeToggle
        theme={theme}
        onToggle={() => setTheme((prev) => (prev === "light" ? "dark" : "light"))}
      />

      <section className="hero">
        <div className="hero__text">
          <p className="hero__eyebrow">GÜNLÜK HABER BÜLTENİ</p>
          <h1>Haber Özetleri</h1>
          <p className="hero__lead">
            Günün manşetlerinden seçilen haberler kartlara sığdırıldı; tek dokunuşla detaylı özetleri açabilirsiniz.
          </p>
          <div className="hero__actions">
            <ViewToggle value={viewMode} onChange={setViewMode} />
          </div>
        </div>
      </section>

      <section className="content-layout">
        <div className="content-main">
          {error ? (
            <div className="error-state">{error}</div>
          ) : (
            <div className={`news-grid news-grid--${viewMode}`}>
              {visibleEntries.map((entry) => (
                <NewsCard key={entry.id} entry={entry} />
              ))}
              {hasMoreEntries && <div ref={sentinelRef} className="infinite-sentinel" aria-hidden="true" />}
            </div>
          )}
        </div>
        <aside className="sources-panel">
          <SourceSelector
            sources={sources}
            value={selectedSource}
            onChange={setSelectedSource}
            disabled={loading}
          />
        </aside>
      </section>
    </div>
  );
}
