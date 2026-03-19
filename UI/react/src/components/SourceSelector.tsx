interface SourceSelectorProps {
  sources: string[];
  value: string | null;
  onChange: (next: string) => void;
  disabled?: boolean;
}

export function SourceSelector({
  sources,
  value,
  onChange,
  disabled
}: SourceSelectorProps) {
  if (!sources.length) {
    return (
      <div className="source-panel source-panel--empty" aria-label="Haber kaynakları">
        <div className="source-panel__header">
          <h1>Haber Kaynakları</h1>
        </div>
        <p className="muted">Yeni yayınlar aktarıldığında burada listelenecek.</p>
      </div>
    );
  }

  return (
    <div className="source-panel" aria-label="Haber kaynakları">
      <div className="source-panel__header">
        <h1>Haber Kaynakları</h1>
      </div>
      <ul className="source-panel__list">
        {sources.map((source) => {
          const isActive = value === source;
          return (
            <li key={source}>
              <button
                type="button"
                className={`source-pill ${isActive ? "active" : ""}`}
                onClick={() => onChange(source)}
                disabled={disabled}
                aria-pressed={isActive}
              >
                <span className="source-pill__name">{source}</span>
                {isActive && <span className="source-pill__dot" aria-hidden="true" />}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}




