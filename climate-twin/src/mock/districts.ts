/* ─────────────────────────────────────────────────────────────────────────────
   mock/districts.ts
   Complete mock dataset for Indian districts.
   Used by: Dashboard, Climate Twin, Risk Analysis, Simulator.
───────────────────────────────────────────────────────────────────────────── */

export type RiskLevel = "Low" | "Medium" | "High" | "Critical"
export type Region    = "North" | "South" | "East" | "West" | "Central" | "Northeast"

export interface Coordinates {
  lat: number
  lng: number
}

export interface DistrictClimate {
  /** Unique district ID */
  id: string
  /** District name */
  name: string
  /** State name */
  state: string
  /** Broad geographic region */
  region: Region
  /** Approximate center coordinates */
  coordinates: Coordinates
  /** Estimated population (millions) */
  populationM: number

  /* ── Atmospheric ──────────────────────────────────────────────── */
  /** Land surface temperature in °C */
  temperature: number
  /** Deviation from 30-year mean (°C) */
  temperatureAnomaly: number
  /** Annual cumulative rainfall (mm) */
  rainfall: number
  /** Deviation from normal rainfall (%) */
  rainfallAnomaly: number
  /** Relative humidity (%) */
  humidity: number
  /** Air Quality Index (0–500, US AQI scale) */
  aqi: number
  /** CO₂ concentration (ppm) */
  co2: number
  /** Wind speed (km/h) */
  windSpeed: number

  /* ── Land & Soil ──────────────────────────────────────────────── */
  /** NDVI index (-1 to +1) */
  ndvi: number
  /** Soil moisture index (0–1) */
  soilMoisture: number
  /** Drought severity index (0–5, Palmer scale) */
  droughtIndex: number

  /* ── Risk ─────────────────────────────────────────────────────── */
  /** Composite climate risk level */
  risk: RiskLevel
  /** Numeric risk score 0–100 */
  riskScore: number
}

/* ── Data ─────────────────────────────────────────────────────────────────── */
export const DISTRICTS: DistrictClimate[] = [
  {
    id: "RJ-BAR", name: "Barmer",      state: "Rajasthan", region: "West",
    coordinates: { lat: 25.75, lng: 71.39 }, populationM: 2.6,
    temperature: 46.2, temperatureAnomaly: +3.1, rainfall: 210,  rainfallAnomaly: -38, humidity: 18, aqi: 185, co2: 422.1, windSpeed: 22,
    ndvi: 0.12, soilMoisture: 0.08, droughtIndex: 4.2,
    risk: "Critical", riskScore: 94,
  },
  {
    id: "RJ-JAI", name: "Jaisalmer",   state: "Rajasthan", region: "West",
    coordinates: { lat: 26.91, lng: 70.90 }, populationM: 0.7,
    temperature: 44.8, temperatureAnomaly: +2.8, rainfall: 178,  rainfallAnomaly: -42, humidity: 16, aqi: 172, co2: 421.4, windSpeed: 26,
    ndvi: 0.09, soilMoisture: 0.06, droughtIndex: 4.5,
    risk: "Critical", riskScore: 92,
  },
  {
    id: "RJ-BIK", name: "Bikaner",     state: "Rajasthan", region: "West",
    coordinates: { lat: 28.02, lng: 73.31 }, populationM: 2.4,
    temperature: 43.5, temperatureAnomaly: +2.5, rainfall: 256,  rainfallAnomaly: -31, humidity: 22, aqi: 160, co2: 421.0, windSpeed: 20,
    ndvi: 0.16, soilMoisture: 0.11, droughtIndex: 3.8,
    risk: "Critical", riskScore: 88,
  },
  {
    id: "AS-KAZ", name: "Kaziranga",   state: "Assam",     region: "Northeast",
    coordinates: { lat: 26.58, lng: 93.17 }, populationM: 0.9,
    temperature: 31.2, temperatureAnomaly: +0.8, rainfall: 2840, rainfallAnomaly: +22, humidity: 88, aqi:  62, co2: 419.2, windSpeed:  8,
    ndvi: 0.78, soilMoisture: 0.91, droughtIndex: 0.1,
    risk: "High", riskScore: 82,
  },
  {
    id: "AS-DIB", name: "Dibrugarh",   state: "Assam",     region: "Northeast",
    coordinates: { lat: 27.48, lng: 94.91 }, populationM: 1.3,
    temperature: 30.1, temperatureAnomaly: +0.6, rainfall: 2640, rainfallAnomaly: +18, humidity: 85, aqi:  58, co2: 419.0, windSpeed:  7,
    ndvi: 0.72, soilMoisture: 0.88, droughtIndex: 0.0,
    risk: "High", riskScore: 78,
  },
  {
    id: "MH-YAV", name: "Yavatmal",    state: "Maharashtra", region: "Central",
    coordinates: { lat: 20.39, lng: 78.12 }, populationM: 2.8,
    temperature: 38.4, temperatureAnomaly: +1.9, rainfall: 820,  rainfallAnomaly: -22, humidity: 44, aqi: 110, co2: 420.5, windSpeed: 14,
    ndvi: 0.31, soilMoisture: 0.28, droughtIndex: 2.9,
    risk: "High", riskScore: 77,
  },
  {
    id: "MH-WAR", name: "Wardha",      state: "Maharashtra", region: "Central",
    coordinates: { lat: 20.75, lng: 78.60 }, populationM: 1.3,
    temperature: 37.9, temperatureAnomaly: +1.7, rainfall: 850,  rainfallAnomaly: -20, humidity: 46, aqi: 105, co2: 420.4, windSpeed: 13,
    ndvi: 0.33, soilMoisture: 0.30, droughtIndex: 2.7,
    risk: "High", riskScore: 74,
  },
  {
    id: "MH-AMR", name: "Amravati",    state: "Maharashtra", region: "Central",
    coordinates: { lat: 20.93, lng: 77.75 }, populationM: 2.9,
    temperature: 38.1, temperatureAnomaly: +1.8, rainfall: 880,  rainfallAnomaly: -18, humidity: 48, aqi: 108, co2: 420.3, windSpeed: 12,
    ndvi: 0.34, soilMoisture: 0.31, droughtIndex: 2.6,
    risk: "High", riskScore: 72,
  },
  {
    id: "TN-CHE", name: "Chennai",     state: "Tamil Nadu", region: "South",
    coordinates: { lat: 13.08, lng: 80.27 }, populationM: 7.1,
    temperature: 34.0, temperatureAnomaly: +1.2, rainfall: 1200, rainfallAnomaly: -8,  humidity: 74, aqi: 130, co2: 420.8, windSpeed: 18,
    ndvi: 0.42, soilMoisture: 0.50, droughtIndex: 1.2,
    risk: "Medium", riskScore: 61,
  },
  {
    id: "TN-CUD", name: "Cuddalore",   state: "Tamil Nadu", region: "South",
    coordinates: { lat: 11.74, lng: 79.76 }, populationM: 2.6,
    temperature: 33.2, temperatureAnomaly: +1.0, rainfall: 1380, rainfallAnomaly: -4,  humidity: 78, aqi: 118, co2: 420.6, windSpeed: 20,
    ndvi: 0.48, soilMoisture: 0.56, droughtIndex: 0.8,
    risk: "Medium", riskScore: 58,
  },
  {
    id: "HP-KUL", name: "Kullu",       state: "Himachal Pradesh", region: "North",
    coordinates: { lat: 31.96, lng: 77.10 }, populationM: 0.4,
    temperature: 18.4, temperatureAnomaly: +1.6, rainfall: 1500, rainfallAnomaly: +5,  humidity: 62, aqi:  28, co2: 418.2, windSpeed:  9,
    ndvi: 0.68, soilMoisture: 0.65, droughtIndex: 0.2,
    risk: "Medium", riskScore: 49,
  },
  {
    id: "HP-MAN", name: "Manali",      state: "Himachal Pradesh", region: "North",
    coordinates: { lat: 32.24, lng: 77.19 }, populationM: 0.1,
    temperature: 12.1, temperatureAnomaly: +2.1, rainfall: 1200, rainfallAnomaly: +2,  humidity: 55, aqi:  22, co2: 417.8, windSpeed: 11,
    ndvi: 0.58, soilMoisture: 0.72, droughtIndex: 0.0,
    risk: "Medium", riskScore: 46,
  },
  {
    id: "KL-EKM", name: "Ernakulam",   state: "Kerala",    region: "South",
    coordinates: { lat: 9.98,  lng: 76.28 }, populationM: 3.3,
    temperature: 29.8, temperatureAnomaly: +0.5, rainfall: 2850, rainfallAnomaly: +15, humidity: 82, aqi:  48, co2: 419.1, windSpeed:  6,
    ndvi: 0.75, soilMoisture: 0.88, droughtIndex: 0.0,
    risk: "Low", riskScore: 28,
  },
  {
    id: "KA-BAN", name: "Bengaluru",   state: "Karnataka", region: "South",
    coordinates: { lat: 12.97, lng: 77.59 }, populationM: 12.8,
    temperature: 28.4, temperatureAnomaly: +0.9, rainfall: 970,  rainfallAnomaly: -6,  humidity: 58, aqi:  92, co2: 420.1, windSpeed: 10,
    ndvi: 0.45, soilMoisture: 0.48, droughtIndex: 0.9,
    risk: "Low", riskScore: 32,
  },
  {
    id: "DL-DEL", name: "New Delhi",   state: "Delhi",     region: "North",
    coordinates: { lat: 28.61, lng: 77.21 }, populationM: 19.8,
    temperature: 36.8, temperatureAnomaly: +1.4, rainfall: 750,  rainfallAnomaly: -12, humidity: 42, aqi: 188, co2: 422.0, windSpeed: 15,
    ndvi: 0.22, soilMoisture: 0.24, droughtIndex: 1.8,
    risk: "Medium", riskScore: 55,
  },
  {
    id: "MH-MUM", name: "Mumbai",      state: "Maharashtra", region: "West",
    coordinates: { lat: 19.08, lng: 72.88 }, populationM: 20.4,
    temperature: 32.1, temperatureAnomaly: +0.7, rainfall: 2200, rainfallAnomaly: +8,  humidity: 80, aqi: 125, co2: 420.9, windSpeed: 16,
    ndvi: 0.38, soilMoisture: 0.60, droughtIndex: 0.4,
    risk: "Medium", riskScore: 44,
  },
  {
    id: "WB-KOL", name: "Kolkata",     state: "West Bengal", region: "East",
    coordinates: { lat: 22.57, lng: 88.36 }, populationM: 14.8,
    temperature: 33.5, temperatureAnomaly: +1.0, rainfall: 1600, rainfallAnomaly: +3,  humidity: 76, aqi: 142, co2: 421.2, windSpeed: 12,
    ndvi: 0.40, soilMoisture: 0.62, droughtIndex: 0.6,
    risk: "Medium", riskScore: 50,
  },
  {
    id: "PB-LUD", name: "Ludhiana",    state: "Punjab",    region: "North",
    coordinates: { lat: 30.90, lng: 75.85 }, populationM: 3.5,
    temperature: 35.2, temperatureAnomaly: +1.3, rainfall: 680,  rainfallAnomaly: -18, humidity: 38, aqi: 155, co2: 421.5, windSpeed: 14,
    ndvi: 0.55, soilMoisture: 0.38, droughtIndex: 2.1,
    risk: "High", riskScore: 70,
  },
  {
    id: "OR-BHU", name: "Bhubaneswar", state: "Odisha",    region: "East",
    coordinates: { lat: 20.30, lng: 85.84 }, populationM: 1.0,
    temperature: 34.0, temperatureAnomaly: +1.1, rainfall: 1500, rainfallAnomaly: -2,  humidity: 70, aqi:  88, co2: 420.0, windSpeed: 14,
    ndvi: 0.52, soilMoisture: 0.55, droughtIndex: 0.7,
    risk: "Low", riskScore: 35,
  },
  {
    id: "GJ-AHM", name: "Ahmedabad",   state: "Gujarat",   region: "West",
    coordinates: { lat: 23.02, lng: 72.57 }, populationM: 7.7,
    temperature: 38.9, temperatureAnomaly: +1.8, rainfall: 750,  rainfallAnomaly: -15, humidity: 35, aqi: 148, co2: 421.3, windSpeed: 18,
    ndvi: 0.28, soilMoisture: 0.22, droughtIndex: 2.4,
    risk: "High", riskScore: 68,
  },
]

/** Lookup a district by its ID */
export function getDistrict(id: string): DistrictClimate | undefined {
  return DISTRICTS.find((d) => d.id === id)
}

/** Filter districts by risk level */
export function getDistrictsByRisk(risk: RiskLevel): DistrictClimate[] {
  return DISTRICTS.filter((d) => d.risk === risk)
}

/** Filter districts by region */
export function getDistrictsByRegion(region: Region): DistrictClimate[] {
  return DISTRICTS.filter((d) => d.region === region)
}

/** Summary stats across all districts */
export const DISTRICT_SUMMARY = {
  total:            DISTRICTS.length,
  critical:         DISTRICTS.filter((d) => d.risk === "Critical").length,
  high:             DISTRICTS.filter((d) => d.risk === "High").length,
  medium:           DISTRICTS.filter((d) => d.risk === "Medium").length,
  low:              DISTRICTS.filter((d) => d.risk === "Low").length,
  avgTemperature:   +(DISTRICTS.reduce((s, d) => s + d.temperature, 0) / DISTRICTS.length).toFixed(1),
  avgRainfall:      Math.round(DISTRICTS.reduce((s, d) => s + d.rainfall, 0) / DISTRICTS.length),
  avgAqi:           Math.round(DISTRICTS.reduce((s, d) => s + d.aqi, 0) / DISTRICTS.length),
  avgRiskScore:     Math.round(DISTRICTS.reduce((s, d) => s + d.riskScore, 0) / DISTRICTS.length),
} as const
