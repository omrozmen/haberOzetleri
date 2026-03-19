type ViewMode = "grid" | "list";

interface ViewToggleProps {
  value: ViewMode;
  onChange: (next: ViewMode) => void;
}

export function ViewToggle({ value, onChange }: ViewToggleProps) {
  return (
    <div className="view-toggle" role="group" aria-label="Görünüm seçici">
      <button
        type="button"
        className={value === "grid" ? "active" : ""}
        onClick={() => onChange("grid")}
        aria-label="Kart görünüm"
      >
        <span aria-hidden="true">⧉</span>
      </button>
      <button
        type="button"
        className={value === "list" ? "active" : ""}
        onClick={() => onChange("list")}
        aria-label="Liste görünüm"
      >
        <span aria-hidden="true">☰</span>
      </button>
    </div>
  );
}

