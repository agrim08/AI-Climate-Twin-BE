import * as React from "react"
import { cn } from "@/lib/utils"
import { TrendingUp, TrendingDown, Minus } from "lucide-react"

export type Trend = "up" | "down" | "neutral"

export interface StatCardProps extends React.ComponentProps<"div"> {
  /** The metric label shown above the value */
  label: string
  /** The primary numeric or string value to display */
  value: React.ReactNode
  /** Unit suffix shown next to the value (e.g. "ppm", "°C", "%") */
  unit?: string
  /** Percentage change string (e.g. "+2.4%") */
  change?: string
  /** Direction of the change for color-coding */
  trend?: Trend
  /**
   * Whether an upward trend is good (green) or bad (red).
   * For CO₂, upTrendIsGood=false makes "up" red.
   * For NDVI, upTrendIsGood=true makes "up" green.
   * @default true
   */
  upTrendIsGood?: boolean
  /** Optional icon placed in the top-right corner */
  icon?: React.ReactNode
  /** Adds a subtle colored gradient accent bar at the top of the card */
  accent?: "emerald" | "teal" | "blue" | "amber" | "rose" | "violet"
  /** Shows a skeleton loading state */
  loading?: boolean
}

const accentStyles: Record<NonNullable<StatCardProps["accent"]>, string> = {
  emerald: "from-emerald-500 to-teal-500",
  teal: "from-teal-500 to-cyan-500",
  blue: "from-blue-500 to-indigo-500",
  amber: "from-amber-400 to-orange-500",
  rose: "from-rose-500 to-pink-500",
  violet: "from-violet-500 to-purple-500",
}

const trendIconProps = { className: "size-3.5 shrink-0", "aria-hidden": true }

function TrendBadge({
  trend,
  change,
  upTrendIsGood,
}: {
  trend: Trend
  change: string
  upTrendIsGood: boolean
}) {
  const isPositive =
    (trend === "up" && upTrendIsGood) || (trend === "down" && !upTrendIsGood)
  const isNegative =
    (trend === "up" && !upTrendIsGood) || (trend === "down" && upTrendIsGood)

  const colors = isPositive
    ? "text-emerald-600 bg-emerald-500/10 dark:text-emerald-400 dark:bg-emerald-400/10"
    : isNegative
      ? "text-rose-600 bg-rose-500/10 dark:text-rose-400 dark:bg-rose-400/10"
      : "text-muted-foreground bg-muted/60"

  const Icon =
    trend === "up"
      ? TrendingUp
      : trend === "down"
        ? TrendingDown
        : Minus

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
        colors
      )}
    >
      <Icon {...trendIconProps} />
      {change}
    </span>
  )
}

/**
 * StatCard — a compact metric display card used across dashboards.
 *
 * Features:
 * - Color-coded trend badge (up/down/neutral) with semantic meaning via `upTrendIsGood`
 * - Optional accent gradient bar at the top
 * - Icon slot for contextual glyphs (Lucide icons work great here)
 * - Skeleton loading state
 *
 * @example
 * <StatCard
 *   label="CO₂ Concentration"
 *   value="418.5"
 *   unit="ppm"
 *   change="+1.2%"
 *   trend="up"
 *   upTrendIsGood={false}
 *   accent="rose"
 *   icon={<Wind className="size-5" />}
 * />
 */
function StatCard({
  label,
  value,
  unit,
  change,
  trend = "neutral",
  upTrendIsGood = true,
  icon,
  accent,
  loading = false,
  className,
  ...props
}: StatCardProps) {
  return (
    <div
      className={cn(
        "group relative flex flex-col overflow-hidden rounded-xl",
        "bg-card text-card-foreground ring-1 ring-foreground/10",
        "transition-all duration-200 hover:shadow-md dark:hover:shadow-black/30",
        className
      )}
      {...props}
    >
      {/* Accent bar */}
      {accent && (
        <div
          className={cn(
            "h-0.5 w-full bg-gradient-to-r",
            accentStyles[accent]
          )}
          aria-hidden
        />
      )}

      <div className="flex flex-col gap-3 p-5">
        {/* Top row: label + icon */}
        <div className="flex items-start justify-between gap-2">
          <p className="text-sm font-medium text-muted-foreground leading-snug">
            {loading ? (
              <span className="inline-block h-4 w-28 animate-pulse rounded bg-muted" />
            ) : (
              label
            )}
          </p>
          {icon && !loading && (
            <span className="shrink-0 text-muted-foreground/70 mt-0.5">
              {icon}
            </span>
          )}
        </div>

        {/* Value */}
        <div className="flex items-baseline gap-1.5">
          {loading ? (
            <span className="inline-block h-8 w-24 animate-pulse rounded bg-muted" />
          ) : (
            <>
              <span className="text-2xl font-bold tracking-tight leading-none">
                {value}
              </span>
              {unit && (
                <span className="text-sm text-muted-foreground font-medium">
                  {unit}
                </span>
              )}
            </>
          )}
        </div>

        {/* Trend badge */}
        {change && !loading && (
          <TrendBadge
            trend={trend}
            change={change}
            upTrendIsGood={upTrendIsGood}
          />
        )}
        {loading && (
          <span className="inline-block h-5 w-16 animate-pulse rounded-full bg-muted" />
        )}
      </div>
    </div>
  )
}

export { StatCard }
