import * as React from "react"
import {
  Card as ShadcnCard,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
  CardAction,
} from "@/components/ui/card"
import { cn } from "@/lib/utils"

export interface CardProps extends Omit<React.ComponentProps<typeof ShadcnCard>, "title"> {
  /** Optional header title string or ReactNode */
  title?: React.ReactNode
  /** Optional description rendered below the title */
  description?: React.ReactNode
  /** Optional ReactNode rendered in the top-right action slot */
  action?: React.ReactNode
  /** Optional footer content */
  footer?: React.ReactNode
  /** Enable glassmorphism style for use on gradient/image backgrounds */
  glass?: boolean
  /** Enable a subtle glow border for highlight cards */
  glow?: boolean
}

/**
 * App-level Card component.
 * Wraps shadcn Card and exposes a convenient composition API:
 * - Renders `title`, `description`, and `action` inside a CardHeader automatically.
 * - Wraps `children` in CardContent.
 * - Renders `footer` in CardFooter when provided.
 * - Adds `glass` mode (backdrop-blur + transparency) for overlay cards.
 * - Adds `glow` mode (emerald border glow) for featured metric cards.
 *
 * @example
 * <Card title="CO₂ Levels" description="ppm 30-day average" action={<Badge>Live</Badge>}>
 *   <p>418 ppm</p>
 * </Card>
 */
function Card({
  className,
  title,
  description,
  action,
  footer,
  glass = false,
  glow = false,
  children,
  ...props
}: CardProps) {
  const hasHeader = title || description || action

  return (
    <ShadcnCard
      className={cn(
        "transition-shadow duration-200",
        glass && [
          "bg-white/10 dark:bg-black/20 backdrop-blur-md",
          "ring-1 ring-white/20 dark:ring-white/10",
        ],
        glow && [
          "ring-1 ring-emerald-500/40 shadow-lg shadow-emerald-500/10",
          "dark:ring-emerald-400/30 dark:shadow-emerald-400/10",
        ],
        !glass && !glow && "hover:shadow-md dark:hover:shadow-black/30",
        className
      )}
      {...props}
    >
      {hasHeader && (
        <CardHeader>
          {title && <CardTitle>{title}</CardTitle>}
          {description && <CardDescription>{description}</CardDescription>}
          {action && <CardAction>{action}</CardAction>}
        </CardHeader>
      )}

      {children && <CardContent>{children}</CardContent>}

      {footer && <CardFooter>{footer}</CardFooter>}
    </ShadcnCard>
  )
}

export {
  Card,
  // Re-export shadcn sub-components so callers can still compose manually
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
  CardAction,
}
