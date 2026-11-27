export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <div role="status" className="text-muted flex items-center justify-center gap-3 p-10 text-sm">
      <span className="border-line border-t-pine size-4 animate-spin rounded-full border-2" />
      {label}
    </div>
  );
}

export function ErrorBanner({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div
      role="alert"
      className="bg-alert-soft text-alert flex items-center justify-between gap-3 rounded-xl px-4 py-3 text-sm"
    >
      <span>{message}</span>
      {onRetry && (
        <button className="shrink-0 font-semibold underline" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}
