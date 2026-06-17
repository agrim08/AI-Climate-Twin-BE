/**
 * Barrel export for all reusable app-level components.
 *
 * Usage:
 *   import { Button, Card, StatCard, SectionHeading, PageHeader, Loader, ChartContainer } from "@/components"
 */

export { Button, buttonVariants } from "./Button"
export type { ButtonProps } from "./Button"

export {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
  CardAction,
} from "./Card"
export type { CardProps } from "./Card"

export { StatCard } from "./StatCard"
export type { StatCardProps, Trend } from "./StatCard"

export { SectionHeading } from "./SectionHeading"
export type { SectionHeadingProps } from "./SectionHeading"

export { PageHeader } from "./PageHeader"
export type { PageHeaderProps, Breadcrumb } from "./PageHeader"

export { Loader, LoaderOverlay } from "./Loader"
export type { LoaderProps, LoaderOverlayProps, LoaderSize, LoaderVariant } from "./Loader"

export { ChartContainer } from "./ChartContainer"
export type { ChartContainerProps } from "./ChartContainer"
