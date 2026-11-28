/** One small outline set, 1.75 stroke, always decorative: meaning is also in the text. */
const PATHS = {
  check: "M4 10.5l4 4 8-9",
  warning: "M10 3l8 14H2L10 3zm0 5.5v4m0 2.2v.3",
  info: "M10 18a8 8 0 100-16 8 8 0 000 16zm0-8.5V14m0-8v.3",
  note: "M5 3h10v14l-5-3.5L5 17V3z",
  star: "M10 2.8l2.2 4.6 5 .7-3.6 3.5.9 5-4.5-2.4-4.5 2.4.9-5L2.8 8.1l5-.7L10 2.8z",
  arrow: "M4 10h12m-4-4l4 4-4 4",
} as const;

interface Props {
  name: keyof typeof PATHS;
  filled?: boolean;
  className?: string;
}

export default function Icon({ name, filled = false, className = "" }: Props) {
  return (
    <svg
      aria-hidden="true"
      focusable="false"
      viewBox="0 0 20 20"
      fill={filled ? "currentColor" : "none"}
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      // An arrow points the way the text reads.
      className={`size-4 shrink-0 ${name === "arrow" ? "rtl:-scale-x-100" : ""} ${className}`}
    >
      <path d={PATHS[name]} />
    </svg>
  );
}
