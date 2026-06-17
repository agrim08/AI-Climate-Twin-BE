import type { Metadata } from "next"
import { Geist, Geist_Mono } from "next/font/google"
import "./globals.css"

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
})

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
})

export const metadata: Metadata = {
  title: {
    default: "ClimateTwin India — AI-Powered Climate Intelligence",
    template: "%s · ClimateTwin India",
  },
  description:
    "Real-time satellite-derived climate analytics powered by ISRO constellation data. Monitor, simulate, and predict climate risks across India.",
  keywords: ["climate", "ISRO", "satellite", "AI", "India", "NDVI", "CO2", "analytics"],
}

/**
 * Root layout — provides global fonts, dark class, and CSS.
 * AppShell is mounted per route-group, NOT here, so the landing
 * page can be shell-free while dashboard pages get sidebar+topbar.
 */
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={`dark ${geistSans.variable} ${geistMono.variable} h-full`}
    >
      <body className="h-full antialiased">
        {children}
      </body>
    </html>
  )
}
