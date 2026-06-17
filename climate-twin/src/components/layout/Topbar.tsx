"use client"

import * as React from "react"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import {
  Menu,
  Bell,
  Wifi,
  WifiOff,
  RefreshCw,
  ChevronRight,
} from "lucide-react"
import { Button } from "@/components/Button"

/* ── Route → breadcrumb label map ─────────────────────────────────────── */
const ROUTE_LABELS: Record<string, string> = {
  "/dashboard":      "Dashboard",
  "/climate-twin":   "Climate Twin",
  "/simulator":      "Simulator",
  "/ai-copilot":     "AI Copilot",
  "/risk-analysis":  "Risk Analysis",
}

function useBreadcrumbs(pathname: string) {
  if (pathname === "/") return [{ label: "Dashboard", href: "/" }]

  const segments = pathname.split("/").filter(Boolean)
  return [
    { label: "ClimateTwin", href: "/" },
    ...segments.map((seg, i) => {
      const href = "/" + segments.slice(0, i + 1).join("/")
      const label =
        ROUTE_LABELS[href] ??
        seg.charAt(0).toUpperCase() + seg.slice(1)
      return { label, href }
    }),
  ]
}

/* ── Live status indicator ─────────────────────────────────────────────── */
type DataStatus = "live" | "offline" | "syncing"

function StatusPill({ status }: { status: DataStatus }) {
  return (
    <div
      className={cn(
        "flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium",
        status === "live"
          ? "border-climate-emerald/30 bg-climate-emerald/10 text-climate-emerald"
          : status === "syncing"
            ? "border-climate-amber/30 bg-climate-amber/10 text-climate-amber"
            : "border-border bg-muted text-muted-foreground"
      )}
      aria-label={`Data feed: ${status}`}
    >
      {status === "live" ? (
        <>
          <span className="relative flex size-1.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-climate-emerald opacity-75" />
            <span className="relative inline-flex size-1.5 rounded-full bg-climate-emerald" />
          </span>
          Live
        </>
      ) : status === "syncing" ? (
        <>
          <RefreshCw className="size-3 animate-spin" aria-hidden />
          Syncing
        </>
      ) : (
        <>
          <WifiOff className="size-3" aria-hidden />
          Offline
        </>
      )}
    </div>
  )
}

/* ── Props ─────────────────────────────────────────────────────────────── */
export interface TopbarProps {
  /** Controls the mobile sidebar open state */
  onMobileMenuOpen?: () => void
  /** Current data feed status */
  dataStatus?: DataStatus
  /** Alert count shown on the bell icon */
  alertCount?: number
  /** Last sync timestamp string */
  lastSynced?: string
}

/* ── Topbar ────────────────────────────────────────────────────────────── */
/**
 * Fixed top bar rendered across every page.
 *
 * Contains:
 * - Mobile hamburger menu toggle
 * - Breadcrumb trail auto-derived from the current pathname
 * - Live data feed status pill
 * - Last synced timestamp
 * - Notifications bell with badge
 */
export function Topbar({
  onMobileMenuOpen,
  dataStatus = "live",
  alertCount = 3,
  lastSynced,
}: TopbarProps) {
  const pathname = usePathname()
  const breadcrumbs = useBreadcrumbs(pathname)

  return (
    <header
      className={cn(
        "flex h-14 shrink-0 items-center gap-3 border-b border-border",
        "bg-background/80 backdrop-blur-md px-4",
        "sticky top-0 z-30 w-full"
      )}
      aria-label="Top navigation bar"
    >
      {/* Mobile menu toggle */}
      <Button
        variant="ghost"
        size="icon"
        aria-label="Open navigation menu"
        className="shrink-0 md:hidden"
        onClick={onMobileMenuOpen}
      >
        <Menu className="size-5" aria-hidden />
      </Button>

      {/* ── Breadcrumbs ─────────────────────────────────────────── */}
      <nav aria-label="Breadcrumb" className="flex flex-1 items-center overflow-hidden">
        <ol className="flex min-w-0 items-center gap-1 text-sm">
          {breadcrumbs.map((crumb, i) => {
            const isLast = i === breadcrumbs.length - 1
            return (
              <React.Fragment key={crumb.href}>
                {i > 0 && (
                  <ChevronRight
                    className="size-3.5 shrink-0 text-muted-foreground/50"
                    aria-hidden
                  />
                )}
                <li className="flex min-w-0 items-center">
                  {isLast ? (
                    <span
                      aria-current="page"
                      className="truncate font-semibold text-foreground"
                    >
                      {crumb.label}
                    </span>
                  ) : (
                    <a
                      href={crumb.href}
                      className="truncate text-muted-foreground transition-colors hover:text-foreground"
                    >
                      {crumb.label}
                    </a>
                  )}
                </li>
              </React.Fragment>
            )
          })}
        </ol>
      </nav>

      {/* ── Right controls ──────────────────────────────────────── */}
      <div className="flex shrink-0 items-center gap-2">
        {/* Last synced — hidden on small screens */}
        {lastSynced && (
          <span className="hidden text-xs text-muted-foreground lg:block">
            Synced {lastSynced}
          </span>
        )}

        {/* Live status pill — hidden on very small screens */}
        <div className="hidden sm:block">
          <StatusPill status={dataStatus} />
        </div>

        {/* Notifications bell */}
        <div className="relative">
          <Button
            id="topbar-notifications"
            variant="ghost"
            size="icon"
            aria-label={
              alertCount > 0
                ? `${alertCount} unread notifications`
                : "Notifications"
            }
          >
            <Bell className="size-4" aria-hidden />
          </Button>
          {alertCount > 0 && (
            <span
              aria-hidden
              className="absolute right-1 top-1 flex size-4 items-center justify-center rounded-full bg-climate-rose text-[9px] font-bold text-white"
            >
              {alertCount > 9 ? "9+" : alertCount}
            </span>
          )}
        </div>
      </div>
    </header>
  )
}
