// Small line icons so the dashboard needs no icon library.

const PATHS: Record<string, string> = {
  bag: "M6 7h12l-1 13H7L6 7Zm3 0a3 3 0 0 1 6 0",
  home: "M4 11 12 4l8 7v9h-5v-6H9v6H4v-9Z",
  tag: "M3 12V4h8l10 10-8 8L3 12Zm5-4h.01",
  play: "M8 5v14l11-7L8 5Z",
  check: "M5 12.5 10 17l9-10",
  arrow: "M5 12h14m-5-5 5 5-5 5",
  shield: "M12 3 5 6v6c0 4 3 7.5 7 9 4-1.5 7-5 7-9V6l-7-3Z",
  bolt: "M13 3 5 14h6l-1 7 8-11h-6l1-7Z",
  tool: "M14 6a4 4 0 0 0-5 5L4 16l4 4 5-5a4 4 0 0 0 5-5l-3 3-3-1-1-3 3-3Z",
  chat: "M4 5h16v11H9l-5 4V5Z",
  reset: "M4 4v6h6M20 20v-6h-6M5 13a7 7 0 0 0 13 3M19 11A7 7 0 0 0 6 8",
  bank: "M3 10h18L12 4 3 10Zm2 0v8m4-8v8m6-8v8m4-8v8M3 20h18",
  alert: "M12 4 2 20h20L12 4Zm0 6v4m0 3h.01",
  x: "M6 6l12 12M18 6 6 18",
  spark: "M12 3v4m0 10v4M3 12h4m10 0h4M6 6l2.5 2.5M15.5 15.5 18 18M18 6l-2.5 2.5M8.5 15.5 6 18",
};

export function Icon({ name, size = 18, className }: { name: keyof typeof PATHS | string; size?: number; className?: string }) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d={PATHS[name] ?? PATHS.spark} />
    </svg>
  );
}

export const TYPE_ICON: Record<string, string> = {
  customer_order: "bag",
  rent_notice: "home",
  price_override: "tag",
};
