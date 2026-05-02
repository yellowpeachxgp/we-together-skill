import { Search, X } from "lucide-react";
import { useEffect, useState } from "react";
import type { RefObject } from "react";

export type CommandItem = {
  id: string;
  group: string;
  label: string;
  meta: string;
  keywords: string;
  run: () => void | Promise<void>;
};

type CommandPaletteProps = {
  inputRef: RefObject<HTMLInputElement | null>;
  query: string;
  items: CommandItem[];
  onQueryChange: (value: string) => void;
  onActivate: (item: CommandItem) => void;
  onClose: () => void;
};

export function CommandPalette({
  inputRef,
  query,
  items,
  onQueryChange,
  onActivate,
  onClose
}: CommandPaletteProps) {
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    setActiveIndex(0);
  }, [query]);

  useEffect(() => {
    setActiveIndex((current) => Math.min(current, Math.max(items.length - 1, 0)));
  }, [items.length]);

  const activeItem = items[activeIndex];

  return (
    <div className="command-overlay" role="presentation" onMouseDown={(event) => {
      if (event.target === event.currentTarget) onClose();
    }}>
      <section className="command-dialog glass-panel" role="dialog" aria-label="命令面板" aria-modal="true">
        <header className="command-head">
          <div>
            <p className="eyebrow">Command</p>
            <h3>命令面板</h3>
          </div>
          <button className="icon-button" type="button" aria-label="关闭命令面板" onClick={onClose}>
            <X size={15} />
          </button>
        </header>
        <label className="command-search">
          <Search size={16} aria-hidden="true" />
          <input
            ref={inputRef}
            aria-label="命令搜索"
            aria-activedescendant={activeItem ? `command-item-${activeItem.id}` : undefined}
            autoFocus
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Escape") {
                event.preventDefault();
                onClose();
                return;
              }
              if (event.key === "ArrowDown" && items.length) {
                event.preventDefault();
                setActiveIndex((current) => (current + 1) % items.length);
                return;
              }
              if (event.key === "ArrowUp" && items.length) {
                event.preventDefault();
                setActiveIndex((current) => (current - 1 + items.length) % items.length);
                return;
              }
              if (event.key === "Home" && items.length) {
                event.preventDefault();
                setActiveIndex(0);
                return;
              }
              if (event.key === "End" && items.length) {
                event.preventDefault();
                setActiveIndex(items.length - 1);
                return;
              }
              if (event.key === "Enter" && !event.nativeEvent.isComposing && activeItem) {
                event.preventDefault();
                onActivate(activeItem);
              }
            }}
            placeholder="Jump to view / node"
          />
        </label>
        <div className="command-results">
          {items.length ? (
            items.map((item, index) => (
              <button
                aria-label={`${item.label} ${item.meta}`}
                aria-selected={index === activeIndex}
                className={`command-result ${index === activeIndex ? "is-active" : ""}`}
                id={`command-item-${item.id}`}
                key={item.id}
                type="button"
                onMouseMove={() => setActiveIndex(index)}
                onClick={() => onActivate(item)}
              >
                <span>{item.group}</span>
                <strong>{item.label}</strong>
                <small>{item.meta}</small>
              </button>
            ))
          ) : (
            <p className="command-empty">No command</p>
          )}
        </div>
      </section>
    </div>
  );
}
