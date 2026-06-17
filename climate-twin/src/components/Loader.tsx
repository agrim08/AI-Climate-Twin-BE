import * as React from "react"
import { cn } from "@/lib/utils"

export type LoaderSize = "xs" | "sm" | "md" | "lg" | "xl"
export type LoaderVariant = "spinner" | "dots" | "pulse" | "bars"

const sizeMap: Record<LoaderSize, { wrapper: string; spinner: string }> = {
  xs: { wrapper: "size-4", spinner: "border-[2px]" },
  sm: { wrapper: "size-5", spinner: "border-[2px]" },
  md: { wrapper: "size-8", spinner: "border-[3px]" },
  lg: { wrapper: "size-12", spinner: "border-[3px]" },
  xl: { wrapper: "size-16", spinner: "border-4" },
}

/* ── Spinner ────────────────────────────────────────────────── */
function SpinnerLoader({ size }: { size: LoaderSize }) {
  const { wrapper, spinner } = sizeMap[size]
  return (
    <div
      className={cn(
        "rounded-full border-current border-t-transparent animate-spin",
        "text-emerald-500",
        wrapper,
        spinner
      )}
      role="status"
      aria-label="Loading"
    />
  )
}

/* ── Dots ───────────────────────────────────────────────────── */
function DotsLoader({ size }: { size: LoaderSize }) {
  const dotSize =
    size === "xs" || size === "sm"
      ? "size-1.5"
      : size === "md"
        ? "size-2"
        : "size-2.5"

  return (
    <div className="flex items-center gap-1.5" role="status" aria-label="Loading">
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          style={{ animationDelay: `${i * 160}ms` }}
          className={cn(
            "rounded-full bg-emerald-500 animate-bounce",
            dotSize
          )}
        />
      ))}
    </div>
  )
}

/* ── Pulse ──────────────────────────────────────────────────── */
function PulseLoader({ size }: { size: LoaderSize }) {
  const { wrapper } = sizeMap[size]
  return (
    <div
      className={cn(
        "rounded-full bg-emerald-500/20 animate-pulse",
        "flex items-center justify-center",
        wrapper
      )}
      role="status"
      aria-label="Loading"
    >
      <div
        className={cn(
          "rounded-full bg-emerald-500",
          size === "xs" || size === "sm"
            ? "size-2"
            : size === "md"
              ? "size-3"
              : "size-4"
        )}
      />
    </div>
  )
}

/* ── Bars ───────────────────────────────────────────────────── */
function BarsLoader({ size }: { size: LoaderSize }) {
  const barH =
    size === "xs" || size === "sm" ? "h-3" : size === "md" ? "h-5" : "h-7"
  const barW = size === "xs" || size === "sm" ? "w-0.5" : "w-1"

  return (
    <div
      className="flex items-end gap-0.5"
      role="status"
      aria-label="Loading"
    >
      {[0, 1, 2, 3].map((i) => (
        <div
          key={i}
          style={{
            animationDelay: `${i * 100}ms`,
            animationDuration: "0.8s",
          }}
          className={cn(
            "rounded-full bg-emerald-500 animate-bounce origin-bottom",
            barH,
            barW
          )}
        />
      ))}
    </div>
  )
}

/* ── Overlay ────────────────────────────────────────────────── */
export interface LoaderOverlayProps {
  children?: React.ReactNode
  label?: string
}

/**
 * A full-area overlay (position: absolute or relative) with a
 * semi-transparent backdrop and centered Loader. Useful inside
 * cards and chart containers while data is fetching.
 */
function LoaderOverlay({ children, label = "Loading…" }: LoaderOverlayProps) {
  return (
    <div
      className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 rounded-xl bg-background/70 backdrop-blur-sm"
      role="status"
      aria-label={label}
    >
      <SpinnerLoader size="md" />
      {children ?? (
        <p className="text-sm text-muted-foreground animate-pulse">{label}</p>
      )}
    </div>
  )
}

/* ── Main export ────────────────────────────────────────────── */
export interface LoaderProps extends React.ComponentProps<"div"> {
  /** Visual style variant */
  variant?: LoaderVariant
  /** Size of the loader indicator */
  size?: LoaderSize
  /** When true, renders the loader centered in its full parent area */
  fullPage?: boolean
  /** Optional message shown below the loader when fullPage=true */
  label?: string
}

/**
 * Loader — a versatile loading indicator.
 *
 * Variants:
 * - `spinner`: circular spinner (default)
 * - `dots`: bouncing dots
 * - `pulse`: pulsing circle
 * - `bars`: animated bars (good for data-loading contexts)
 *
 * @example
 * <Loader />                           // default spinner, inline
 * <Loader variant="dots" size="lg" /> // large bouncing dots
 * <Loader fullPage label="Fetching satellite data…" />
 */
function Loader({
  variant = "spinner",
  size = "md",
  fullPage = false,
  label = "Loading…",
  className,
  ...props
}: LoaderProps) {
  const indicator =
    variant === "spinner" ? (
      <SpinnerLoader size={size} />
    ) : variant === "dots" ? (
      <DotsLoader size={size} />
    ) : variant === "pulse" ? (
      <PulseLoader size={size} />
    ) : (
      <BarsLoader size={size} />
    )

  if (fullPage) {
    return (
      <div
        className={cn(
          "flex min-h-[60vh] flex-col items-center justify-center gap-4",
          className
        )}
        {...props}
      >
        {indicator}
        <p className="text-sm text-muted-foreground animate-pulse">{label}</p>
      </div>
    )
  }

  return (
    <div
      className={cn("inline-flex items-center justify-center", className)}
      {...props}
    >
      {indicator}
    </div>
  )
}

export { Loader, LoaderOverlay }
