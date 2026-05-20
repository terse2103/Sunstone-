interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  retryLabel?: string;
}

export function ErrorState({
  title = "Something went wrong",
  message,
  onRetry,
  retryLabel = "Retry",
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className="rounded-xl border border-danger-500/30 bg-danger-500/5 p-4 text-sm text-ink-800 md:p-5"
    >
      <p className="font-semibold text-danger-500">{title}</p>
      <p className="mt-1 text-ink-700">{message}</p>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 inline-flex min-h-[44px] items-center rounded-md border border-ink-200 bg-white px-4 py-2 text-sm font-medium text-ink-800 hover:bg-ink-100"
        >
          {retryLabel}
        </button>
      ) : null}
    </div>
  );
}
