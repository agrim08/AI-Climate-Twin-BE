"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import {
  LayoutDashboard,
  Globe2,
  FlaskConical,
  Bot,
  ShieldAlert,
  ChevronLeft,
  Satellite,
} from "lucide-react"

/* ── Nav item definitions ──────────────────────────────────────────────── */
interface NavItem {
  label: string
  href: string
  icon: React.ElementType
  badge?: string
}

interface NavGroup {
  label: string
  items: NavItem[]
}

const NAV_GROUPS: NavGroup[] = [
  {
    label: "Main",
    items: [
      { label: "Dashboard",     href: "/dashboard",     icon: LayoutDashboard },
      { label: "Climate Twin",  href: "/climate-twin",  icon: Globe2          },
      { label: "Simulator",     href: "/simulator",     icon: FlaskConical    },
      { label: "AI Copilot",    href: "/ai-copilot",    icon: Bot             },
      { label: "Risk Analysis", href: "/risk-analysis", icon: ShieldAlert, badge: "3" },
    ],
  },
]

/* ── Props ─────────────────────────────────────────────────────────────── */
export interface SidebarProps {
  collapsed: boolean
  onToggle: () => void
}

/* ── NavLink ───────────────────────────────────────────────────────────── */
function NavLink({
  item,
  collapsed,
  active,
}: {
  item: NavItem
  collapsed: boolean
  active: boolean
}) {
  const Icon = item.icon

  return (
    <Link
      href={item.href}
      title={collapsed ? item.label : undefined}
      aria-current={active ? "page" : undefined}
      className={cn(
        "group flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium",
        "transition-all duration-150 ease-out",
        active
          ? "bg-primary/15 text-primary shadow-[inset_0_0_0_1px] shadow-primary/20"
          : "text-muted-foreground hover:bg-secondary hover:text-foreground",
        collapsed && "justify-center px-2"
      )}
    >
      <Icon
        className={cn(
          "shrink-0 transition-colors duration-150",
          active
            ? "text-primary"
            : "text-muted-foreground group-hover:text-foreground",
          collapsed ? "size-5" : "size-4"
        )}
        aria-hidden
      />

      {!collapsed && (
        <>
          <span className="flex-1 truncate">{item.label}</span>
          {item.badge && (
            <span className="inline-flex size-5 items-center justify-center rounded-full bg-climate-rose/20 text-[10px] font-bold text-climate-rose">
              {item.badge}
            </span>
          )}
        </>
      )}

      {/* Collapsed badge dot */}
      {collapsed && item.badge && (
        <span
          aria-label={`${item.badge} alerts`}
          className="absolute right-1.5 top-1.5 size-2 rounded-full bg-climate-rose"
        />
      )}
    </Link>
  )
}

/* ── Sidebar ───────────────────────────────────────────────────────────── */
/**
 * Collapsible left sidebar with grouped navigation.
 * Controlled by parent via `collapsed` / `onToggle`.
 *
 * Highlights the active route via Next.js `usePathname`.
 */
export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const pathname = usePathname()

  return (
    <aside
      id="app-sidebar"
      aria-label="Main navigation"
      className={cn(
        "relative flex h-full flex-col border-r border-border bg-sidebar",
        "transition-[width] duration-300 ease-in-out will-change-[width]",
        collapsed ? "w-14" : "w-60"
      )}
    >
      {/* ── Brand ─────────────────────────────────────────────────── */}
      <div
        className={cn(
          "flex h-14 shrink-0 items-center gap-3 border-b border-border px-3",
          collapsed && "justify-center px-2"
        )}
      >
        {/* Logo mark */}
        <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-climate-emerald to-climate-teal shadow-lg shadow-climate-emerald/20">
          <Satellite className="size-4 text-white" aria-hidden />
        </div>

        {!collapsed && (
          <div className="flex min-w-0 flex-col leading-none">
            <span className="truncate text-sm font-bold tracking-tight text-foreground">
              ClimateTwin
            </span>
            <span className="truncate text-[10px] font-medium text-muted-foreground">
              AI Intelligence
            </span>
          </div>
        )}
      </div>

      {/* ── Nav groups ────────────────────────────────────────────── */}
      <nav className="flex flex-1 flex-col gap-1 overflow-y-auto overflow-x-hidden p-2">
        {NAV_GROUPS.map((group) => (
          <div key={group.label} className="mb-2">
            {!collapsed && (
              <p className="mb-1 px-3 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/60">
                {group.label}
              </p>
            )}
            {collapsed && <div className="mb-1 mx-auto w-6 border-t border-border/60" />}
            <ul className="flex flex-col gap-0.5" role="list">
              {group.items.map((item) => (
                <li key={item.href} className="relative">
                  <NavLink
                    item={item}
                    collapsed={collapsed}
                    active={
                      item.href === "/"
                        ? pathname === "/"
                        : pathname.startsWith(item.href)
                    }
                  />
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      {/* ── Collapse toggle ───────────────────────────────────────── */}
      <div className="shrink-0 border-t border-border p-2">
        <button
          id="sidebar-toggle"
          onClick={onToggle}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          aria-expanded={!collapsed}
          aria-controls="app-sidebar"
          className={cn(
            "flex w-full items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium text-muted-foreground",
            "transition-colors hover:bg-secondary hover:text-foreground",
            collapsed && "justify-center px-2"
          )}
        >
          <ChevronLeft
            className={cn(
              "size-4 shrink-0 transition-transform duration-300",
              collapsed && "rotate-180"
            )}
            aria-hidden
          />
          {!collapsed && <span>Collapse</span>}
        </button>
      </div>
    </aside>
  )
}
