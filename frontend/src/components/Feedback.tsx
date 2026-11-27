import Icon from "./Icons";

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div role="status" className="text-muted flex items-center gap-3 py-4 text-sm">
      <span
        aria-hidden="true"
        className="border-line border-t-pine size-4 animate-spin rounded-full border-2"
      />
      {label}
    </div>
  );
}

export function ErrorBanner({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div
      role="alert"
      className="bg-alert-soft text-alert rounded-control flex items-center gap-3 px-4 py-2 text-sm"
    >
      <Icon name="warning" />
      <span className="flex-1">{message}</span>
      {onRetry && (
        <button className="min-h-10 shrink-0 font-semibold underline" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}
