import { useMemo, useState } from "react";
import type { KeyboardEvent, MouseEvent } from "react";
import type { NewsEntry } from "../types";

interface NewsCardProps {
  entry: NewsEntry;
}

export function NewsCard({ entry }: NewsCardProps) {
  const [isOpen, setIsOpen] = useState(false);
  const host = useMemo(() => {
    if (!entry.url) return null;
    try {
      return new URL(entry.url).hostname.replace(/^www\./, "");
    } catch {
      return null;
    }
  }, [entry.url]);

  const handleToggle = (
    event?: MouseEvent<HTMLElement> | KeyboardEvent<HTMLElement>
  ) => {
    if (event) {
      const target = event.target as HTMLElement;
      if (target.closest("a[href]")) {
        return;
      }
    }
    setIsOpen((prev) => !prev);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      handleToggle(event);
    }
  };

  return (
    <article
      className={`news-card ${isOpen ? "open" : ""}`}
      role="button"
      tabIndex={0}
      aria-expanded={isOpen}
      onClick={handleToggle}
      onKeyDown={handleKeyDown}
    >
      <header>
        <div className="title-block">
          <div className="title-wrapper">
            <h3>
              <span className="title-text">{entry.title}</span>
            </h3>
          </div>
        </div>
      </header>

      <div className="summary" data-state={isOpen ? "expanded" : "collapsed"} aria-hidden={!isOpen}>
        {entry.summary ? (
          <p>{entry.summary}</p>
        ) : (
          <p className="muted">Bu kayıt için özet bulunamadı.</p>
        )}
      </div>

      {entry.url && isOpen && (
        <p className="source">
          <span className="source-label">Kaynak</span>
          <a
            className="source-link"
            href={entry.url}
            target="_blank"
            rel="noreferrer"
            aria-label={`${entry.title} haberini ${host ?? "kaynak"} üzerinde aç`}
          >
            {entry.title}
          </a>
        </p>
      )}
    </article>
  );
}
