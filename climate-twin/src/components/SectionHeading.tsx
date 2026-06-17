import * as React from "react"
import { cn } from "@/lib/utils"

export interface SectionHeadingProps extends Omit<React.ComponentProps<"div">, "title"> {
  /** The heading text — rendered as an `h2` by default */
  title: React.ReactNode
  /** Optional subtitle rendered below the title */
  subtitle?: React.ReactNode
  /** Optionally override the heading level */
  as?: "h1" | "h2" | "h3" | "h4"
  /** Renders action elements (e.g. a button) aligned to the right */
  actions?: React.ReactNode
  /**
   * Visual accent before the title:
   * - "bar": a vertical colored bar on the left (default)
   * - "dot": a glowing dot before the text
   * - "none": no accent
   */
  accent?: "bar" | "dot" | "none"
  /** If true, renders a full-width divider under the heading */
  divider?: boolean
}

/**
 * SectionHeading — a reusable section title component.
 *
 * Renders a visually consistent heading with optional subtitle,
 * right-aligned actions, and decorative accent.
 *
 * @example
 * <SectionHeading
 *   title="Climate Overview"
 *   subtitle="Last 30 days · 3 regions selected"
 *   accent="bar"
 *   actions={<Button size="sm">Export</Button>}
 *   divider
 * />
 */
function SectionHeading({
  title,
  subtitle,
  as: Tag = "h2",
  actions,
  accent = "bar",
  divider = false,
  className,
  ...props
}: SectionHeadingProps) {
  return (
    <div className={cn("flex flex-col gap-3", className)} {...props}>
      <div className="flex items-start justify-between gap-4">
        {/* Title + accent */}
        <div
          className={cn(
            "flex items-start gap-3",
            accent === "bar" && "pl-4 relative"
          )}
        >
          {/* Vertical accent bar */}
          {accent === "bar" && (
            <span
              aria-hidden
              className="absolute left-0 top-0.5 h-full w-1 rounded-full bg-gradient-to-b from-emerald-500 to-teal-500"
            />
          )}

          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              {/* Glowing dot accent */}
              {accent === "dot" && (
                <span
                  aria-hidden
                  className="mt-px inline-flex size-2 shrink-0 rounded-full bg-emerald-500 shadow-[0_0_6px_2px] shadow-emerald-500/50"
                />
              )}
              <Tag className="font-heading text-lg font-semibold leading-snug tracking-tight text-foreground">
                {title}
              </Tag>
            </div>
            {subtitle && (
              <p className="text-sm text-muted-foreground leading-snug">
                {subtitle}
              </p>
            )}
          </div>
        </div>

        {/* Right-aligned actions */}
        {actions && (
          <div className="flex shrink-0 items-center gap-2">{actions}</div>
        )}
      </div>

      {/* Optional divider */}
      {divider && (
        <hr className="border-border" />
      )}
    </div>
  )
}

export { SectionHeading }
