import { MODEL_LABELS, MODEL_SEQUENCE, type ModelType } from "../config";

interface ModelToggleProps {
  value: ModelType;
  onChange: (next: ModelType) => void;
}

export function ModelToggle({ value, onChange }: ModelToggleProps) {
  return (
    <div className="model-toggle" role="group" aria-label="Model seçici">
      {MODEL_SEQUENCE.map((option) => (
        <button
          key={option}
          type="button"
          className={option === value ? "active" : ""}
          onClick={() => onChange(option)}
        >
          {MODEL_LABELS[option]}
        </button>
      ))}
    </div>
  );
}

