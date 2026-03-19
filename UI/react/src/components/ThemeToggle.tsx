interface ThemeToggleProps {
  theme: "light" | "dark";
  onToggle: () => void;
}

export function ThemeToggle({ theme, onToggle }: ThemeToggleProps) {
  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={onToggle}
      aria-label="Tema değiştir"
      title="Tema değiştir"
    >
      {theme === "dark" ? "☀️" : "🌙"}
    </button>
  );
}







