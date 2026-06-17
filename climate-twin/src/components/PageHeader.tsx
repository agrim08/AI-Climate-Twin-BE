import * as React from "react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/Button"
import { ArrowLeft } from "lucide-react"

export interface Breadcrumb {
  label: string
  href?: string
}

export interface PageHeaderProps extends Omit<React.ComponentProps<"header">, "title"> {
  /** Main page title — rendered as an `h1` */
  title: React.ReactNode
  /** Optional subtitle or description */
  subtitle?: React.ReactNode
  /** Breadcrumb navigation items */
  breadcrumbs?: Breadcrumb[]
  /** Action elements rendered on the right (e.g. buttons, dropdowns) */
  actions?: React.ReactNode
  /**
   * When true, renders a back button using Next.js router or a plain anchor.
   * If a string is provided, it's used as the back href.
   */
  back?: boolean | string
  /** Callback when the back button is clicked */
  onBack?: () => void
  /** If true, adds a full-width bottom border divider */
  divider?: boolean
  /** Compact mode reduces vertical padding */
  compact?: boolean
}

/**
 * PageHeader — the top-level heading block for any dashboard page.
 *
 * Renders:
 * - Optional breadcrumb trail
 * - Optional back button
 * - A prominent `h1` title with optional subtitle
 * - Right-aligned actions (buttons, filters, etc.)
 * - Optional bottom divider
 *
 * Designed to sit at the very top of a page's content area.
 *
 * @example
 * <PageHeader
 *   title="Regional Climate Analysis"
 *   subtitle="Rajasthan · June 2025"
 *   breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Regions" }]}
 *   actions={<Button appVariant="glow">Run Simulation</Button>}
 *   divider
 * />
 */
function PageHeader({
  title,
  subtitle,
  breadcrumbs,
  actions,
  back,
  onBack,
  divider = true,
  compact = false,
  className,
  ...props
}: PageHeaderProps) {
  const backHref = typeof back === "string" ? back : undefined

  return (
    <header
      className={cn(
        "flex flex-col gap-3 w-full",
        compact ? "py-4" : "py-6",
        divider && "border-b border-border pb-5",
        className
      )}
      {...props}
    >
      {/* Breadcrumbs */}
      {breadcrumbs && breadcrumbs.length > 0 && (
        <nav aria-label="Breadcrumb">
          <ol className="flex items-center gap-1.5 text-xs text-muted-foreground">
            {breadcrumbs.map((crumb, i) => (
              <React.Fragment key={i}>
                {i > 0 && (
                  <li aria-hidden className="select-none">
                    /
                  </li>
                )}
                <li>
                  {crumb.href ? (
                    <a
                      href={crumb.href}
                      className="hover:text-foreground transition-colors duration-150 underline-offset-2 hover:underline"
                    >
                      {crumb.label}
                    </a>
                  ) : (
                    <span className="text-foreground font-medium">
                      {crumb.label}
                    </span>
                  )}
                </li>
              </React.Fragment>
            ))}
          </ol>
        </nav>
      )}

      {/* Main row: back + title + actions */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          {/* Back button */}
          {back && (
            <Button
              variant="outline"
              size="icon"
              aria-label="Go back"
              className="mt-0.5 shrink-0"
              onClick={onBack}
              {...(backHref ? { as: "a", href: backHref } : {})}
            >
              <ArrowLeft className="size-4" />
            </Button>
          )}

          {/* Title block */}
          <div className="flex flex-col gap-1">
            <h1
              className={cn(
                "font-heading font-bold leading-tight tracking-tight text-foreground",
                compact ? "text-xl" : "text-2xl sm:text-3xl"
              )}
            >
              {title}
            </h1>
            {subtitle && (
              <p className="text-sm text-muted-foreground leading-snug">
                {subtitle}
              </p>
            )}
          </div>
        </div>

        {/* Actions */}
        {actions && (
          <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
            {actions}
          </div>
        )}
      </div>
    </header>
  )
}

export { PageHeader }
