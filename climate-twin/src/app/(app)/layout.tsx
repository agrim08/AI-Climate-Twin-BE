import type { Metadata } from "next"
import { AppShell } from "@/components/layout"

export const metadata: Metadata = {
  title: "Dashboard",
}

/**
 * App route-group layout.
 * Every page inside (app)/ gets the full sidebar + topbar shell.
 */
export default function AppLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="h-full overflow-hidden">
      <AppShell>{children}</AppShell>
    </div>
  )
}
