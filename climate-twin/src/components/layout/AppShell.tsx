"use client"

import * as React from "react"
import { cn } from "@/lib/utils"
import { Sidebar } from "./Sidebar"
import { Topbar } from "./Topbar"

/* ── Mobile overlay ────────────────────────────────────────────────────── */
function MobileOverlay({
  open,
  onClose,
}: {
  open: boolean
  onClose: () => void
}) {
  if (!open) return null
  return (
    <div
      aria-hidden
      className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm md:hidden"
      onClick={onClose}
    />
  )
}

/* ── Props ─────────────────────────────────────────────────────────────── */
export interface AppShellProps {
  children: React.ReactNode
  /** Override the data feed status shown in the Topbar */
  dataStatus?: "live" | "offline" | "syncing"
  /** Override alert count shown in the Topbar notification badge */
  alertCount?: number
}

/* ── AppShell ──────────────────────────────────────────────────────────── */
/**
 * The master layout shell for all Climate Twin pages.
 *
 * Renders:
 * - Collapsible left Sidebar (desktop) / slide-in drawer (mobile)
 * - Sticky Topbar with breadcrumbs, status, and notifications
 * - Scrollable main content area with consistent padding
 *
 * Usage — in any page:
 * ```tsx
 * export default function MyPage() {
 *   return (
 *     <AppShell>
 *       <PageHeader title="My Page" />
 *       …content…
 *     </AppShell>
 *   )
 * }
 * ```
 *
 * Or wire it once in a route group layout.tsx so every child page
 * automatically gets the shell without repeating it.
 */
export function AppShell({
  children,
  dataStatus = "live",
  alertCount = 3,
}: AppShellProps) {
  /* Sidebar collapse state — persisted in localStorage */
  const [collapsed, setCollapsed] = React.useState<boolean>(() => {
    if (typeof window === "undefined") return false
    return localStorage.getItem("sidebar-collapsed") === "true"
  })

  /* Mobile sidebar open state */
  const [mobileOpen, setMobileOpen] = React.useState(false)

  const toggleCollapsed = React.useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev
      localStorage.setItem("sidebar-collapsed", String(next))
      return next
    })
  }, [])

  /* Close mobile drawer on route change */
  React.useEffect(() => {
    setMobileOpen(false)
  }, [])

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background">
      {/* ── Desktop sidebar ───────────────────────────────────────── */}
      <div className="hidden md:flex md:shrink-0">
        <Sidebar collapsed={collapsed} onToggle={toggleCollapsed} />
      </div>

      {/* ── Mobile sidebar drawer ─────────────────────────────────── */}
      <MobileOverlay open={mobileOpen} onClose={() => setMobileOpen(false)} />
      <div
        className={cn(
          "fixed inset-y-0 left-0 z-50 md:hidden",
          "transition-transform duration-300 ease-in-out will-change-transform",
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
        aria-hidden={!mobileOpen}
      >
        <Sidebar collapsed={false} onToggle={() => setMobileOpen(false)} />
      </div>

      {/* ── Main column ──────────────────────────────────────────── */}
      <div className="flex flex-1 min-w-0 flex-col overflow-hidden">
        {/* Sticky topbar */}
        <Topbar
          onMobileMenuOpen={() => setMobileOpen(true)}
          dataStatus={dataStatus}
          alertCount={alertCount}
        />

        {/* Scrollable content area */}
        <main
          id="main-content"
          tabIndex={-1}
          className={cn(
            "flex-1 overflow-y-auto overflow-x-hidden",
            "px-4 py-6 sm:px-6 lg:px-8",
            /* Subtle radial glow at top — from globals.css body bg — preserved */
            "focus-visible:outline-none"
          )}
        >
          {/* Page max-width wrapper */}
          <div className="mx-auto w-full max-w-screen-2xl">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
