/* ─────────────────────────────────────────────────────────────────────────────
   mock/risk.ts
   Climate risk events, district risk scores, and historical risk trends.
   Used by: Risk Analysis page, Dashboard alerts, AI Copilot context.
───────────────────────────────────────────────────────────────────────────── */

import type { RiskLevel } from "./districts"

export type RiskEventType =
  | "Heat Wave"
  | "Flash Flood"
  | "Agricultural Drought"
  | "Cyclone"
  | "GLOF"
  | "Landslide"
  | "Cold Wave"
  | "Dust Storm"
  | "Wildfire"
  | "Coastal Erosion"

export type RiskSeverity = "Warning" | "Moderate" | "High" | "Critical"

export interface RiskEvent {
  id: string
  /** Primary state / district region */
  region: string
  /** Specific districts affected */
  districts: string[]
  type: RiskEventType
  severity: RiskSeverity
  /** Composite risk score 0–100 */
  riskScore: number
  /** Estimated affected population in millions */
  affectedPopM: number
  /** Short forecast / implication string */
  forecast: string
  /** When the event was detected / updated */
  updatedAt: string
  /** Whether the event is currently active */
  active: boolean
  /** Linked district IDs from districts.ts */
  districtIds: string[]
  /** Economic impact estimate (USD millions) */
  economicImpactM?: number
  /** Crop loss estimate (%) – for agricultural events */
  cropLossPct?: number
}

export interface RiskTrendPoint {
  /** Date label */
  date: string
  /** National composite risk score */
  riskScore: number
  /** Number of active events */
  activeEvents: number
  /** Number of critical events */
  criticalEvents: number
}

export interface DistrictRiskSummary {
  districtId: string
  name: string
  state: string
  risk: RiskLevel
  riskScore: number
  /** Primary contributing risk driver */
  primaryDriver: string
  temperature: number
  rainfall: number
  aqi: number
}

/* ── Active risk events ───────────────────────────────────────────────────── */
export const RISK_EVENTS: RiskEvent[] = [
  {
    id: "EVT-001",
    region: "Rajasthan",
    districts: ["Barmer", "Jaisalmer", "Bikaner", "Jodhpur"],
    type: "Heat Wave",
    severity: "Critical",
    riskScore: 94,
    affectedPopM: 4.2,
    forecast: "72h sustained >45°C. Night-time low remains above 32°C. Extreme dehydration risk.",
    updatedAt: "2h ago",
    active: true,
    districtIds: ["RJ-BAR", "RJ-JAI", "RJ-BIK"],
    economicImpactM: 180,
  },
  {
    id: "EVT-002",
    region: "Assam",
    districts: ["Kaziranga", "Majuli", "Dibrugarh", "Lakhimpur"],
    type: "Flash Flood",
    severity: "High",
    riskScore: 82,
    affectedPopM: 2.8,
    forecast: "Brahmaputra breach probability 78%. 4 embankments under stress. Evacuation advised.",
    updatedAt: "5h ago",
    active: true,
    districtIds: ["AS-KAZ", "AS-DIB"],
    economicImpactM: 95,
  },
  {
    id: "EVT-003",
    region: "Vidarbha, Maharashtra",
    districts: ["Yavatmal", "Wardha", "Amravati", "Akola"],
    type: "Agricultural Drought",
    severity: "High",
    riskScore: 77,
    affectedPopM: 3.1,
    forecast: "Kharif sowing delayed 3 weeks. Soil moisture at 50-year low. Crop loss est. −25%.",
    updatedAt: "12h ago",
    active: true,
    districtIds: ["MH-YAV", "MH-WAR", "MH-AMR"],
    economicImpactM: 240,
    cropLossPct: 25,
  },
  {
    id: "EVT-004",
    region: "Tamil Nadu Coast",
    districts: ["Chennai", "Cuddalore", "Nagapattinam", "Puducherry"],
    type: "Cyclone",
    severity: "Moderate",
    riskScore: 61,
    affectedPopM: 5.6,
    forecast: "Deep depression in Bay of Bengal. Cat 1–2 landfall probability 45% in 96h.",
    updatedAt: "1h ago",
    active: true,
    districtIds: ["TN-CHE", "TN-CUD"],
    economicImpactM: 60,
  },
  {
    id: "EVT-005",
    region: "Himachal Pradesh",
    districts: ["Kullu", "Manali", "Chamba", "Lahaul"],
    type: "GLOF",
    severity: "Warning",
    riskScore: 49,
    affectedPopM: 0.3,
    forecast: "Glacial lake outburst risk elevated. Snow melt 35% above seasonal average. Monitor advised.",
    updatedAt: "6h ago",
    active: true,
    districtIds: ["HP-KUL", "HP-MAN"],
    economicImpactM: 15,
  },
  {
    id: "EVT-006",
    region: "Punjab",
    districts: ["Ludhiana", "Patiala", "Sangrur"],
    type: "Agricultural Drought",
    severity: "High",
    riskScore: 70,
    affectedPopM: 1.8,
    forecast: "Pre-monsoon deficit −18%. Groundwater table dropped 2.3m. Rice transplantation risk.",
    updatedAt: "8h ago",
    active: true,
    districtIds: ["PB-LUD"],
    economicImpactM: 130,
    cropLossPct: 18,
  },
  {
    id: "EVT-007",
    region: "Gujarat",
    districts: ["Ahmedabad", "Gandhinagar", "Anand"],
    type: "Heat Wave",
    severity: "High",
    riskScore: 68,
    affectedPopM: 3.4,
    forecast: "48h temperature >43°C with humidity spike. Urban heat island amplification in Ahmedabad.",
    updatedAt: "3h ago",
    active: true,
    districtIds: ["GJ-AHM"],
    economicImpactM: 55,
  },
]

/* ── 30-day national risk trend ──────────────────────────────────────────── */
export const RISK_TREND_30D: RiskTrendPoint[] = [
  { date: "May 18", riskScore: 48, activeEvents: 3, criticalEvents: 0 },
  { date: "May 21", riskScore: 51, activeEvents: 3, criticalEvents: 0 },
  { date: "May 24", riskScore: 55, activeEvents: 4, criticalEvents: 1 },
  { date: "May 27", riskScore: 58, activeEvents: 4, criticalEvents: 1 },
  { date: "May 30", riskScore: 60, activeEvents: 5, criticalEvents: 1 },
  { date: "Jun 02", riskScore: 64, activeEvents: 5, criticalEvents: 1 },
  { date: "Jun 05", riskScore: 68, activeEvents: 6, criticalEvents: 2 },
  { date: "Jun 08", riskScore: 72, activeEvents: 6, criticalEvents: 2 },
  { date: "Jun 11", riskScore: 75, activeEvents: 7, criticalEvents: 2 },
  { date: "Jun 14", riskScore: 78, activeEvents: 7, criticalEvents: 3 },
  { date: "Jun 17", riskScore: 82, activeEvents: 7, criticalEvents: 3 },
]

/* ── District risk score leaderboard ─────────────────────────────────────── */
export const DISTRICT_RISK_LEADERBOARD: DistrictRiskSummary[] = [
  { districtId: "RJ-BAR", name: "Barmer",      state: "Rajasthan",   risk: "Critical", riskScore: 94, primaryDriver: "Extreme heat",    temperature: 46.2, rainfall: 210,  aqi: 185 },
  { districtId: "RJ-JAI", name: "Jaisalmer",   state: "Rajasthan",   risk: "Critical", riskScore: 92, primaryDriver: "Drought",         temperature: 44.8, rainfall: 178,  aqi: 172 },
  { districtId: "RJ-BIK", name: "Bikaner",     state: "Rajasthan",   risk: "Critical", riskScore: 88, primaryDriver: "Drought",         temperature: 43.5, rainfall: 256,  aqi: 160 },
  { districtId: "AS-KAZ", name: "Kaziranga",   state: "Assam",       risk: "High",     riskScore: 82, primaryDriver: "Flood risk",      temperature: 31.2, rainfall: 2840, aqi:  62 },
  { districtId: "MH-YAV", name: "Yavatmal",    state: "Maharashtra", risk: "High",     riskScore: 77, primaryDriver: "Agri drought",    temperature: 38.4, rainfall: 820,  aqi: 110 },
  { districtId: "PB-LUD", name: "Ludhiana",    state: "Punjab",      risk: "High",     riskScore: 70, primaryDriver: "Groundwater",     temperature: 35.2, rainfall: 680,  aqi: 155 },
  { districtId: "GJ-AHM", name: "Ahmedabad",   state: "Gujarat",     risk: "High",     riskScore: 68, primaryDriver: "Urban heat",      temperature: 38.9, rainfall: 750,  aqi: 148 },
  { districtId: "TN-CHE", name: "Chennai",     state: "Tamil Nadu",  risk: "Medium",   riskScore: 61, primaryDriver: "Cyclone threat",  temperature: 34.0, rainfall: 1200, aqi: 130 },
  { districtId: "DL-DEL", name: "New Delhi",   state: "Delhi",       risk: "Medium",   riskScore: 55, primaryDriver: "Air quality",     temperature: 36.8, rainfall: 750,  aqi: 188 },
  { districtId: "WB-KOL", name: "Kolkata",     state: "West Bengal", risk: "Medium",   riskScore: 50, primaryDriver: "Urban flood",     temperature: 33.5, rainfall: 1600, aqi: 142 },
]

/* ── Helper functions ────────────────────────────────────────────────────── */

/** Sort risk events by risk score descending */
export const sortedRiskEvents = (events: RiskEvent[] = RISK_EVENTS) =>
  [...events].sort((a, b) => b.riskScore - a.riskScore)

/** Get only active events */
export const activeRiskEvents = RISK_EVENTS.filter((e) => e.active)

/** Risk severity color classes */
export const SEVERITY_STYLES: Record<RiskSeverity, string> = {
  Critical: "bg-climate-rose/15 text-climate-rose border-climate-rose/30",
  High:     "bg-climate-amber/15 text-climate-amber border-climate-amber/30",
  Moderate: "bg-climate-teal/15 text-climate-teal border-climate-teal/30",
  Warning:  "bg-climate-sky/15 text-climate-sky border-climate-sky/30",
}

/** Aggregate economic impact of all active events */
export const totalEconomicImpactM = RISK_EVENTS.reduce(
  (sum, e) => sum + (e.economicImpactM ?? 0),
  0
)
