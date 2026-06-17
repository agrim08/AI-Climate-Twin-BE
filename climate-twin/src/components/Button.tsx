import * as React from "react"
import { Button as ShadcnButton, buttonVariants } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { cva, type VariantProps } from "class-variance-authority"
import { Loader2 } from "lucide-react"
import type { ComponentProps } from "react"

/**
 * Extended button variants for the climate-twin app.
 * Builds on top of the shadcn base while adding app-specific styles:
 * - "glow": vibrant teal/emerald gradient for primary CTA actions
 * - "danger": destructive red button for critical actions
 * Re-exports existing shadcn variants unchanged.
 */
const appButtonVariants = cva("", {
  variants: {
    appVariant: {
      glow: [
        "relative bg-gradient-to-r from-emerald-500 to-teal-500",
        "text-white border-0 shadow-lg shadow-emerald-500/30",
        "hover:from-emerald-400 hover:to-teal-400 hover:shadow-emerald-500/50",
        "active:scale-[0.98] transition-all duration-200",
        "focus-visible:ring-emerald-500/50",
      ].join(" "),
      danger: [
        "bg-red-600/90 text-white border-0",
        "hover:bg-red-500 shadow-md shadow-red-600/20",
        "active:scale-[0.98] transition-all duration-200",
      ].join(" "),
    },
  },
})

export interface ButtonProps
  extends ComponentProps<typeof ShadcnButton>,
    VariantProps<typeof appButtonVariants> {
  /** When true, shows a spinner and disables the button */
  loading?: boolean
  /** Icon rendered to the left of children */
  leftIcon?: React.ReactNode
  /** Icon rendered to the right of children */
  rightIcon?: React.ReactNode
}

/**
 * App-level Button component.
 * Wraps the shadcn Button primitive and adds:
 *   - `loading` state with spinner
 *   - `leftIcon` / `rightIcon` slots
 *   - `appVariant="glow"` for the emerald gradient CTA style
 *   - `appVariant="danger"` for destructive actions
 *
 * All standard shadcn `variant` and `size` props are still supported.
 *
 * @example
 * <Button appVariant="glow" leftIcon={<Plus />}>Add Region</Button>
 * <Button loading>Saving...</Button>
 */
const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      appVariant,
      loading = false,
      leftIcon,
      rightIcon,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    return (
      <ShadcnButton
        ref={ref}
        disabled={disabled || loading}
        className={cn(
          appVariant && appButtonVariants({ appVariant }),
          className
        )}
        {...props}
      >
        {loading ? (
          <Loader2 className="size-4 animate-spin" aria-hidden />
        ) : (
          leftIcon && <span className="shrink-0">{leftIcon}</span>
        )}
        {children}
        {!loading && rightIcon && (
          <span className="shrink-0">{rightIcon}</span>
        )}
      </ShadcnButton>
    )
  }
)

Button.displayName = "Button"

export { Button, buttonVariants }
