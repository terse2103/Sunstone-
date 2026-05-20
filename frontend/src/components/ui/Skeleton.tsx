interface SkeletonProps {
  className?: string;
  label?: string;
}

export function Skeleton({ className = "", label }: SkeletonProps) {
  return (
    <div
      className={`animate-pulse rounded-md bg-ink-200/70 ${className}`}
      role="status"
      aria-label={label ?? "Loading"}
    />
  );
}
