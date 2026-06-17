import * as React from "react"
import { cn } from "@/lib/utils"
import { LoaderOverlay } from "@/components/Loader"
import { SectionHeading } from "@/components/SectionHeading"

export interface ChartContainerProps extends Omit<React.ComponentProps<"div">, "title"> {
  /** Chart title displayed in the heading */
  title?: React.ReactNode
  /** Subtitle/description displayed below the title */
  subtitle?: React.ReactNode
  /** Right-aligned actions (filters, period selectors, download) */
  actions?: React.ReactNode
  /**
   * Minimum height of the chart canvas area.
   * Accepts any valid CSS value (e.g. "300px", "20rem").
   * @default "280px"
   */
  minHeight?: string
  /** When true, renders an overlay spinner over the chart area */
  loading?: boolean
  /** Loading label shown below the spinner */
  loadingLabel?: string
  /**
   * When provided, replaces chart content with an empty-state message.
   * Ideal when a query returns no data.
   */
  empty?: React.ReactNode
  /** Adds a subtle glassmorphism style to the container */
  glass?: boolean
}

/**
 * ChartContainer — a standardised wrapper for all recharts/chart components.
 *
 * Responsibilities:
 * - Renders a consistent SectionHeading above the chart canvas
 * - Provides a `min-height` canvas area that ensures charts render correctly
 * - Handles loading overlay (via `LoaderOverlay`)
 * - Handles empty state rendering
 * - Responsive: uses `ResponsiveContainer` pattern (children fill 100% width)
 *
 * Usage with Recharts:
 * ```tsx
 * <ChartContainer title="Temperature Trend" subtitle="Past 6 months" loading={isFetching}>
 *   <ResponsiveContainer width="100%" height="100%">
 *     <LineChart data={data}>…</LineChart>
 *   </ResponsiveContainer>
 * </ChartContainer>
 * ```
 *
 * @example
 * <ChartContainer
 *   title="CO₂ Levels"
 *   subtitle="Monthly average · ppm"
 *   actions={<Select …/>}
 *   loading={isLoading}
 *   minHeight="320px"
 * >
 *   {chart}
 * </ChartContainer>
 */
function ChartContainer({
  title,
  subtitle,
  actions,
  minHeight = "280px",
  loading = false,
  loadingLabel = "Loading chart data…",
  empty,
  glass = false,
  className,
  children,
  ...props
}: ChartContainerProps) {
  const hasHeader = title || subtitle || actions

  return (
    <div
      className={cn(
        "flex flex-col gap-4 rounded-xl p-5",
        "ring-1 ring-foreground/10",
        glass
          ? "bg-white/10 dark:bg-black/20 backdrop-blur-md ring-white/20"
          : "bg-card text-card-foreground",
        "transition-shadow duration-200 hover:shadow-md dark:hover:shadow-black/30",
        className
      )}
      {...props}
    >
      {/* Header */}
      {hasHeader && (
        <SectionHeading
          title={title ?? ""}
          subtitle={subtitle}
          accent="none"
          actions={actions}
          divider={false}
          className="shrink-0"
        />
      )}

      {/* Chart canvas */}
      <div
        className="relative w-full"
        style={{ minHeight }}
      >
        {/* Loading overlay */}
        {loading && <LoaderOverlay label={loadingLabel} />}

        {/* Empty state */}
        {!loading && empty ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-center">
            {typeof empty === "string" ? (
              <>
                <svg
                  aria-hidden
                  className="size-10 text-muted-foreground/40"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M3 3v18h18M7 16l4-4 4 4 4-6"
                  />
                </svg>
                <p className="text-sm text-muted-foreground">{empty}</p>
              </>
            ) : (
              empty
            )}
          </div>
        ) : (
          /* Chart children fill the container */
          <div className="absolute inset-0">{children}</div>
        )}
      </div>
    </div>
  )
}

export { ChartContainer }
