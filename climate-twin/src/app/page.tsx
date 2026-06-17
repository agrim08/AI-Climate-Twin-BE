import Link from "next/link"
import {
  Satellite,
  ArrowRight,
  Globe2,
  FlaskConical,
  Bot,
  ShieldAlert,
  BarChart3,
  Zap,
  Map,
  Layers,
  CheckCircle2,
  ChevronRight,
  Wind,
  Thermometer,
  Droplets,
  Leaf,
} from "lucide-react"

/* Simple GitHub SVG icon (not in lucide-react) */
function GithubIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className} aria-hidden>
      <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
    </svg>
  )
}

/* ═══════════════════════════════════════════════════════════════════════════
   NAVBAR
═══════════════════════════════════════════════════════════════════════════ */
function Navbar() {
  return (
    <nav className="fixed inset-x-0 top-0 z-50 flex h-16 items-center justify-between border-b border-white/5 bg-background/60 px-6 backdrop-blur-xl">
      {/* Logo */}
      <Link href="/" className="flex items-center gap-2.5 select-none">
        <div className="flex size-8 items-center justify-center rounded-lg bg-gradient-to-br from-climate-emerald to-climate-teal shadow-lg shadow-climate-emerald/30">
          <Satellite className="size-4 text-white" aria-hidden />
        </div>
        <div className="flex flex-col leading-none">
          <span className="text-sm font-bold tracking-tight text-foreground">ClimateTwin</span>
          <span className="text-[10px] font-medium text-muted-foreground">India</span>
        </div>
      </Link>

      {/* Nav links */}
      <div className="hidden items-center gap-6 md:flex">
        {["Features","How It Works","Data Sources","GitHub"].map((item) => (
          <a
            key={item}
            href={item === "GitHub" ? "https://github.com" : `#${item.toLowerCase().replace(/\s+/g,"-")}`}
            className="text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            {item}
          </a>
        ))}
      </div>

      {/* CTA */}
      <div className="flex items-center gap-3">
        <div className="hidden items-center gap-1.5 rounded-full border border-climate-emerald/30 bg-climate-emerald/10 px-2.5 py-1 text-xs font-medium text-climate-emerald sm:flex">
          <span className="relative flex size-1.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-climate-emerald opacity-75" />
            <span className="relative inline-flex size-1.5 rounded-full bg-climate-emerald" />
          </span>
          Live Data
        </div>
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-climate-emerald to-climate-teal px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-climate-emerald/25 transition-all hover:shadow-climate-emerald/40 hover:brightness-110 active:scale-95"
        >
          Launch Dashboard <ArrowRight className="size-3.5" aria-hidden />
        </Link>
      </div>
    </nav>
  )
}

/* ═══════════════════════════════════════════════════════════════════════════
   HERO — EARTH VISUALIZATION
═══════════════════════════════════════════════════════════════════════════ */
function EarthViz() {
  return (
    <div className="relative flex size-[340px] items-center justify-center sm:size-[420px]" aria-hidden>
      {/* Outer ambient glow */}
      <div className="absolute size-[420px] rounded-full bg-climate-emerald/5 animate-glow-pulse sm:size-[520px]" />
      <div className="absolute size-[380px] rounded-full bg-climate-teal/5 animate-glow-pulse sm:size-[460px]" style={{ animationDelay: "1s" }} />

      {/* Orbit ring 1 */}
      <div className="absolute size-[280px] rounded-full border border-climate-emerald/15 sm:size-[340px]">
        {/* Satellite on orbit 1 */}
        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 animate-orbit">
          <div className="flex size-6 items-center justify-center rounded-full bg-climate-emerald/20 border border-climate-emerald/40 shadow-[0_0_8px] shadow-climate-emerald/40">
            <Satellite className="size-3 text-climate-emerald" />
          </div>
        </div>
      </div>

      {/* Orbit ring 2 */}
      <div className="absolute size-[380px] rounded-full border border-climate-teal/10 sm:size-[440px]">
        {/* Satellite on orbit 2 */}
        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 animate-orbit-reverse">
          <div className="flex size-5 items-center justify-center rounded-full bg-climate-sky/20 border border-climate-sky/40 shadow-[0_0_8px] shadow-climate-sky/40">
            <Satellite className="size-2.5 text-climate-sky" />
          </div>
        </div>
      </div>

      {/* Earth globe */}
      <div className="animate-float relative">
        <div
          className="size-48 rounded-full sm:size-60"
          style={{
            background: `
              radial-gradient(ellipse 60% 55% at 35% 40%,
                oklch(0.55 0.15 185) 0%,
                oklch(0.35 0.10 210) 35%,
                oklch(0.20 0.06 240) 65%,
                oklch(0.12 0.03 245) 100%
              )`,
            boxShadow: `
              inset -20px -20px 40px oklch(0.08 0.02 245),
              inset 10px 10px 30px oklch(0.60 0.15 185 / 20%),
              0 0 60px oklch(0.55 0.15 185 / 25%),
              0 0 120px oklch(0.55 0.15 185 / 10%)
            `,
          }}
        >
          {/* Lat/lon grid overlay */}
          <div
            className="absolute inset-0 rounded-full opacity-20"
            style={{
              backgroundImage: `
                repeating-linear-gradient(0deg, oklch(0.8 0 0 / 20%) 0px, oklch(0.8 0 0 / 20%) 1px, transparent 1px, transparent 30px),
                repeating-linear-gradient(90deg, oklch(0.8 0 0 / 20%) 0px, oklch(0.8 0 0 / 20%) 1px, transparent 1px, transparent 30px)
              `,
            }}
          />

          {/* Land mass blobs (India silhouette hint) */}
          <div className="absolute left-[38%] top-[30%] size-10 rounded-[60%_40%_55%_45%] bg-climate-emerald/40 blur-[2px]" />
          <div className="absolute left-[30%] top-[25%] size-6 rounded-full bg-climate-teal/30 blur-[1px]" />
          <div className="absolute left-[55%] top-[40%] size-8 rounded-[50%_60%_40%_50%] bg-climate-emerald/25 blur-[2px]" />
          <div className="absolute left-[20%] top-[50%] size-5 rounded-full bg-climate-sky/20 blur-sm" />

          {/* Atmosphere glow */}
          <div
            className="absolute -inset-1 rounded-full opacity-30"
            style={{
              background: `radial-gradient(ellipse at 30% 30%, oklch(0.72 0.15 185 / 40%) 0%, transparent 60%)`,
            }}
          />

          {/* Hotspot pings */}
          {[
            { top: "35%", left: "42%", color: "bg-climate-emerald", delay: "0s"    },
            { top: "55%", left: "38%", color: "bg-climate-amber",   delay: "0.8s"  },
            { top: "45%", left: "58%", color: "bg-climate-rose",    delay: "1.6s"  },
          ].map(({ top, left, color, delay }, i) => (
            <div key={i} className="absolute" style={{ top, left }}>
              <span className={`relative flex size-2`}>
                <span className={`absolute inline-flex h-full w-full animate-ping rounded-full ${color} opacity-60`} style={{ animationDelay: delay }} />
                <span className={`relative inline-flex size-2 rounded-full ${color}`} />
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Floating data badges */}
      <div className="glass-panel absolute -left-4 top-12 rounded-xl px-3 py-2 text-xs sm:-left-12">
        <div className="flex items-center gap-2">
          <Thermometer className="size-3.5 text-climate-amber" />
          <div>
            <div className="font-bold text-foreground">+1.28°C</div>
            <div className="text-muted-foreground">Anomaly</div>
          </div>
        </div>
      </div>

      <div className="glass-panel absolute -right-4 top-20 rounded-xl px-3 py-2 text-xs sm:-right-12">
        <div className="flex items-center gap-2">
          <Wind className="size-3.5 text-climate-sky" />
          <div>
            <div className="font-bold text-foreground">421 ppm</div>
            <div className="text-muted-foreground">CO₂</div>
          </div>
        </div>
      </div>

      <div className="glass-panel absolute -bottom-2 left-8 rounded-xl px-3 py-2 text-xs sm:bottom-4">
        <div className="flex items-center gap-2">
          <Leaf className="size-3.5 text-climate-emerald" />
          <div>
            <div className="font-bold text-foreground">NDVI 0.63</div>
            <div className="text-muted-foreground">Vegetation</div>
          </div>
        </div>
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════════════════
   HERO SECTION
═══════════════════════════════════════════════════════════════════════════ */
function Hero() {
  return (
    <section
      id="hero"
      className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-6 pt-16"
      aria-label="Hero"
    >
      {/* Background: deep space gradient */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background: `
            radial-gradient(ellipse 80% 60% at 50% -5%,  oklch(0.22 0.06 210 / 30%) 0%, transparent 65%),
            radial-gradient(ellipse 60% 50% at 90% 80%,  oklch(0.18 0.08 162 / 18%) 0%, transparent 55%),
            radial-gradient(ellipse 40% 40% at 10% 60%,  oklch(0.15 0.05 245 / 20%) 0%, transparent 55%),
            oklch(0.09 0.022 245)
          `,
        }}
      />

      {/* Grid overlay */}
      <div className="hero-grid pointer-events-none absolute inset-0 opacity-100" />

      {/* Vignette */}
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-background" />

      <div className="relative z-10 mx-auto flex max-w-7xl flex-col items-center gap-12 lg:flex-row lg:justify-between lg:gap-8">

        {/* Left: text content */}
        <div className="flex max-w-2xl flex-col items-center gap-8 text-center lg:items-start lg:text-left">
          {/* Badge */}
          <div className="animate-fade-up inline-flex items-center gap-2 rounded-full border border-climate-emerald/25 bg-climate-emerald/8 px-4 py-1.5 text-xs font-semibold text-climate-emerald">
            <Satellite className="size-3.5" aria-hidden />
            Bhartiya Antariksh Hackathon · ISRO × AI
          </div>

          {/* Headline */}
          <div className="animate-fade-up-delay flex flex-col gap-3">
            <h1 className="font-heading text-5xl font-black leading-[1.05] tracking-tight text-foreground sm:text-6xl xl:text-7xl">
              Climate<span className="text-gradient-climate">Twin</span>
              <br />
              <span className="text-4xl sm:text-5xl xl:text-6xl">India</span>
            </h1>
            <p className="text-xl font-medium text-muted-foreground sm:text-2xl">
              AI-Powered Climate Intelligence Platform
            </p>
          </div>

          {/* Body text */}
          <p className="animate-fade-up-delay2 max-w-xl text-base text-muted-foreground leading-relaxed">
            Real-time satellite data from ISRO's constellation fused with AI models to monitor,
            simulate, and predict climate risks across every district in India.
          </p>

          {/* CTAs */}
          <div className="animate-fade-up-delay3 flex flex-wrap items-center gap-4">
            <Link
              href="/dashboard"
              className="glow-emerald inline-flex items-center gap-2.5 rounded-xl bg-gradient-to-r from-climate-emerald to-climate-teal px-7 py-3.5 text-base font-bold text-white shadow-2xl shadow-climate-emerald/30 transition-all duration-200 hover:brightness-110 hover:scale-[1.02] active:scale-[0.98]"
            >
              <BarChart3 className="size-5" aria-hidden />
              Launch Dashboard
              <ArrowRight className="size-4" aria-hidden />
            </Link>
            <a
              href="#how-it-works"
              className="inline-flex items-center gap-2 rounded-xl border border-border bg-secondary/50 px-7 py-3.5 text-base font-semibold text-foreground backdrop-blur-sm transition-all hover:bg-secondary hover:border-border/80"
            >
              How It Works
              <ChevronRight className="size-4 text-muted-foreground" aria-hidden />
            </a>
          </div>

          {/* Stats row */}
          <div className="animate-fade-up-delay3 flex flex-wrap items-center gap-6 pt-2">
            {[
              { value: "642",  label: "Districts",       icon: Map        },
              { value: "3",    label: "ISRO Satellites", icon: Satellite  },
              { value: "50+",  label: "Climate Indices", icon: BarChart3  },
              { value: "Live", label: "Data Feed",       icon: Zap        },
            ].map(({ value, label, icon: Icon }) => (
              <div key={label} className="flex items-center gap-2 text-sm">
                <Icon className="size-3.5 text-climate-emerald" aria-hidden />
                <span className="font-bold text-foreground">{value}</span>
                <span className="text-muted-foreground">{label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Right: earth visualization */}
        <div className="shrink-0">
          <EarthViz />
        </div>
      </div>

      {/* Scroll hint */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 text-xs text-muted-foreground/60">
        <div className="h-8 w-5 rounded-full border border-border/50 flex items-start justify-center pt-1.5">
          <div className="size-1 rounded-full bg-muted-foreground/60 animate-bounce" />
        </div>
        Scroll to explore
      </div>
    </section>
  )
}

/* ═══════════════════════════════════════════════════════════════════════════
   FEATURES SECTION
═══════════════════════════════════════════════════════════════════════════ */
const FEATURES = [
  {
    icon: Satellite,
    title: "Real-time Satellite Data",
    desc: "Live feeds from Cartosat-3, RESOURCESAT-2A, and INSAT-3DR. Full coverage of India at 5m–141km resolution across thermal, optical, and microwave bands.",
    color: "from-climate-sky to-climate-teal",
    glow: "group-hover:shadow-climate-sky/15",
  },
  {
    icon: Globe2,
    title: "Digital Earth Twin",
    desc: "A full-fidelity digital replica of India's climate system. Visualise NDVI, CO₂ flux, soil moisture, land surface temperature, and precipitation layers simultaneously.",
    color: "from-climate-emerald to-climate-teal",
    glow: "group-hover:shadow-climate-emerald/15",
  },
  {
    icon: Bot,
    title: "AI Copilot",
    desc: "Ask questions in plain English. 'What is the drought risk in Vidarbha this kharif season?' Get instant, citation-backed answers from satellite data and CMIP6 models.",
    color: "from-violet-500 to-climate-teal",
    glow: "group-hover:shadow-violet-500/15",
  },
  {
    icon: FlaskConical,
    title: "Climate Simulator",
    desc: "Run RCP 4.5 and 8.5 projections with custom parameter overrides. Simulate emission scenarios, deforestation rates, and monsoon variability across 25-year horizons.",
    color: "from-climate-teal to-climate-sky",
    glow: "group-hover:shadow-climate-teal/15",
  },
  {
    icon: ShieldAlert,
    title: "Risk Intelligence",
    desc: "AI-powered risk scoring for all 642 districts. Heat waves, floods, droughts, cyclones, and GLOF events — ranked by severity, affected population, and forecast certainty.",
    color: "from-climate-amber to-climate-rose",
    glow: "group-hover:shadow-climate-amber/15",
  },
  {
    icon: Layers,
    title: "Multi-layer Analytics",
    desc: "Cross-correlate agricultural, hydrological, and atmospheric layers. Detect compound events like simultaneous heatwave + drought that simple single-parameter tools miss.",
    color: "from-climate-rose to-violet-500",
    glow: "group-hover:shadow-climate-rose/15",
  },
]

function Features() {
  return (
    <section id="features" className="relative px-6 py-24 sm:py-32">
      <div className="mx-auto max-w-7xl">
        {/* Header */}
        <div className="mx-auto mb-16 max-w-2xl text-center">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-climate-teal/25 bg-climate-teal/8 px-4 py-1.5 text-xs font-semibold text-climate-teal">
            <Zap className="size-3.5" aria-hidden />
            Platform Capabilities
          </div>
          <h2 className="font-heading text-3xl font-black tracking-tight text-foreground sm:text-4xl">
            Everything you need to{" "}
            <span className="text-gradient-climate">understand India&apos;s climate</span>
          </h2>
          <p className="mt-4 text-base text-muted-foreground leading-relaxed">
            Six integrated modules working in concert — from raw satellite ingestion to
            actionable district-level risk alerts.
          </p>
        </div>

        {/* Feature grid */}
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map(({ icon: Icon, title, desc, color, glow }) => (
            <div
              key={title}
              className={`feature-card group relative overflow-hidden rounded-2xl border border-border bg-card p-6 transition-all duration-300 ${glow}`}
            >
              {/* Gradient icon background blob */}
              <div
                className={`pointer-events-none absolute -right-8 -top-8 size-32 rounded-full bg-gradient-to-br ${color} opacity-5 blur-2xl transition-opacity duration-300 group-hover:opacity-10`}
                aria-hidden
              />

              {/* Icon */}
              <div className={`mb-4 inline-flex size-11 items-center justify-center rounded-xl bg-gradient-to-br ${color} shadow-lg`}>
                <Icon className="size-5 text-white" aria-hidden />
              </div>

              {/* Content */}
              <h3 className="mb-2 font-heading text-base font-bold text-foreground">{title}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">{desc}</p>

              {/* Arrow hint on hover */}
              <div className="mt-4 flex items-center gap-1 text-xs font-semibold text-muted-foreground/0 transition-all group-hover:text-climate-emerald/80">
                Explore <ChevronRight className="size-3" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ═══════════════════════════════════════════════════════════════════════════
   HOW IT WORKS SECTION
═══════════════════════════════════════════════════════════════════════════ */
const STEPS = [
  {
    step: "01",
    icon: Satellite,
    title: "Ingest",
    desc: "Raw imagery and sensor data streamed continuously from ISRO's Cartosat-3, RESOURCESAT-2A, and INSAT-3DR satellites via the NRSC data pipeline.",
    color: "text-climate-sky",
    border: "border-climate-sky/30",
    bg: "bg-climate-sky/10",
  },
  {
    step: "02",
    icon: Layers,
    title: "Process",
    desc: "AI models compute derived indices — NDVI, LST, soil moisture, carbon flux, drought severity — and cross-reference against IMD historical records and CMIP6 projections.",
    color: "text-climate-teal",
    border: "border-climate-teal/30",
    bg: "bg-climate-teal/10",
  },
  {
    step: "03",
    icon: ShieldAlert,
    title: "Analyse",
    desc: "Risk scoring engine evaluates compound climate signals across all 642 districts. Anomaly detection flags deviations from 30-year baselines in near real-time.",
    color: "text-climate-emerald",
    border: "border-climate-emerald/30",
    bg: "bg-climate-emerald/10",
  },
  {
    step: "04",
    icon: Zap,
    title: "Act",
    desc: "Decision-ready insights delivered through the dashboard, AI Copilot natural language queries, exportable PDF risk reports, and API access for downstream systems.",
    color: "text-climate-amber",
    border: "border-climate-amber/30",
    bg: "bg-climate-amber/10",
  },
]

function HowItWorks() {
  return (
    <section
      id="how-it-works"
      className="relative overflow-hidden px-6 py-24 sm:py-32"
    >
      {/* Background accent */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background: `radial-gradient(ellipse 70% 50% at 50% 50%, oklch(0.14 0.04 210 / 60%) 0%, transparent 70%)`,
        }}
      />

      <div className="relative mx-auto max-w-7xl">
        {/* Header */}
        <div className="mx-auto mb-16 max-w-2xl text-center">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-climate-emerald/25 bg-climate-emerald/8 px-4 py-1.5 text-xs font-semibold text-climate-emerald">
            <CheckCircle2 className="size-3.5" aria-hidden />
            The Pipeline
          </div>
          <h2 className="font-heading text-3xl font-black tracking-tight text-foreground sm:text-4xl">
            From raw satellite data to{" "}
            <span className="text-gradient-climate">actionable intelligence</span>
          </h2>
          <p className="mt-4 text-base text-muted-foreground leading-relaxed">
            Four stages — automated, continuous, and running in real-time.
          </p>
        </div>

        {/* Steps */}
        <div className="relative grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {/* Connector line — desktop */}
          <div
            className="pointer-events-none absolute left-0 right-0 top-11 hidden h-px bg-gradient-to-r from-transparent via-border to-transparent lg:block"
            aria-hidden
          />

          {STEPS.map(({ step, icon: Icon, title, desc, color, border, bg }) => (
            <div key={step} className="relative flex flex-col items-center gap-4 text-center">
              {/* Step icon */}
              <div className={`relative z-10 flex size-[88px] flex-col items-center justify-center gap-1 rounded-2xl border ${border} ${bg} shadow-lg`}>
                <Icon className={`size-6 ${color}`} aria-hidden />
                <span className={`text-[10px] font-black uppercase tracking-widest ${color}`}>{step}</span>
              </div>

              {/* Content */}
              <div className="flex flex-col gap-2">
                <h3 className="font-heading text-lg font-bold text-foreground">{title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ═══════════════════════════════════════════════════════════════════════════
   CTA BANNER
═══════════════════════════════════════════════════════════════════════════ */
function CTABanner() {
  return (
    <section className="px-6 py-16">
      <div className="mx-auto max-w-4xl">
        <div
          className="relative overflow-hidden rounded-3xl p-10 text-center"
          style={{
            background: `
              radial-gradient(ellipse 80% 80% at 50% 50%, oklch(0.20 0.06 185 / 60%) 0%, transparent 70%),
              oklch(0.12 0.030 248)
            `,
            boxShadow: `0 0 0 1px oklch(0.72 0.185 162 / 20%), 0 32px 64px oklch(0.09 0.022 245 / 60%)`,
          }}
        >
          {/* Background grid */}
          <div className="hero-grid pointer-events-none absolute inset-0 opacity-50" />

          {/* Glow orb */}
          <div
            className="pointer-events-none absolute left-1/2 top-0 -translate-x-1/2 -translate-y-1/2 size-64 rounded-full opacity-30"
            style={{ background: `radial-gradient(oklch(0.72 0.185 162) 0%, transparent 70%)` }}
            aria-hidden
          />

          <div className="relative">
            <div className="mb-4 inline-flex size-14 items-center justify-center rounded-2xl bg-gradient-to-br from-climate-emerald to-climate-teal shadow-xl shadow-climate-emerald/30">
              <Satellite className="size-7 text-white" aria-hidden />
            </div>
            <h2 className="mb-3 font-heading text-3xl font-black text-foreground sm:text-4xl">
              Ready to explore India&apos;s{" "}
              <span className="text-gradient-climate">climate intelligence?</span>
            </h2>
            <p className="mb-8 text-base text-muted-foreground">
              Live satellite data. AI-driven insights. Zero setup required.
            </p>
            <Link
              href="/dashboard"
              className="glow-emerald inline-flex items-center gap-3 rounded-xl bg-gradient-to-r from-climate-emerald to-climate-teal px-8 py-4 text-base font-bold text-white shadow-2xl shadow-climate-emerald/30 transition-all duration-200 hover:brightness-110 hover:scale-[1.02] active:scale-[0.98]"
            >
              <BarChart3 className="size-5" aria-hidden />
              Launch Dashboard
              <ArrowRight className="size-4" aria-hidden />
            </Link>
          </div>
        </div>
      </div>
    </section>
  )
}

/* ═══════════════════════════════════════════════════════════════════════════
   FOOTER
═══════════════════════════════════════════════════════════════════════════ */
function Footer() {
  return (
    <footer className="border-t border-border px-6 py-10">
      <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-6 sm:flex-row">
        {/* Brand */}
        <div className="flex items-center gap-2.5">
          <div className="flex size-7 items-center justify-center rounded-lg bg-gradient-to-br from-climate-emerald to-climate-teal">
            <Satellite className="size-3.5 text-white" aria-hidden />
          </div>
          <span className="text-sm font-bold tracking-tight text-foreground">ClimateTwin India</span>
        </div>

        {/* Links */}
        <div className="flex flex-wrap items-center justify-center gap-6 text-xs text-muted-foreground">
          {[
            { label: "Dashboard",    href: "/dashboard"    },
            { label: "Climate Twin", href: "/climate-twin" },
            { label: "Simulator",    href: "/simulator"    },
            { label: "AI Copilot",   href: "/ai-copilot"   },
            { label: "Risk Analysis",href: "/risk-analysis" },
          ].map(({ label, href }) => (
            <Link key={label} href={href} className="transition-colors hover:text-foreground">
              {label}
            </Link>
          ))}
        </div>

        {/* Meta */}
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <a href="https://github.com" className="flex items-center gap-1.5 transition-colors hover:text-foreground" aria-label="GitHub">
            <GithubIcon className="size-4" />
            <span className="hidden sm:inline">GitHub</span>
          </a>
          <span className="hidden sm:block">·</span>
          <span>ISRO × AI · Bhartiya Antariksh Hackathon 2025</span>
        </div>
      </div>

      <div className="mx-auto mt-6 max-w-7xl text-center text-xs text-muted-foreground/50">
        © 2025 ClimateTwin India. Built for the Bhartiya Antariksh Hackathon.
        Data sourced from ISRO NRSC, IMD, and CMIP6 model ensembles.
      </div>
    </footer>
  )
}

/* ═══════════════════════════════════════════════════════════════════════════
   PAGE
═══════════════════════════════════════════════════════════════════════════ */
export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <Navbar />
      <Hero />
      <Features />
      <HowItWorks />
      <CTABanner />
      <Footer />
    </div>
  )
}
