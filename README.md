# 🌍 AI Climate Twin India Backend

Welcome to the **AI Climate Twin India Backend**! This repository serves as the production-ready FastAPI backend and advanced machine learning pipeline for building a digital twin of India's climate.

The goal of this system is not just to forecast the weather, but to model complex, long-term climate dynamics (Temperature, Rainfall, Drought Evolution) and support **Scenario Simulations** for climate adaptation, water resource management, and agricultural planning.

---

## 🌟 What We Are Building

The AI Climate Twin models climate patterns at a localized city/district level using decades of historical climate data (ERA5) and state-of-the-art machine learning models.

### Key Capabilities
1. **Temperature Forecasting**: Accurate prediction of surface temperatures using historical lags and rolling trends.
2. **Rainfall & Monsoon Intelligence**: Predicts rainfall while dynamically classifying monsoon phases (Weak/Normal/Strong) using scientifically backed IMD 6-phase encoding.
3. **Drought Intelligence Layer**: Engineers 70+ complex features, calculates localized drought severity indices (CDSS), analyzes physical drivers, triggers early warning alerts, and models agricultural and water stress indices.
4. **Extreme Weather Intelligence Subsystem**: Dual-model cascade predicting Heatwave and Extreme Rainfall classifications and continuous severity indices. Implements compound event risk aggregation, health impact alerts (Green/Yellow/Orange/Red), drainage alerts, and flash flood advisories.
5. **Scenario Simulation Engine**: Natively supports "what-if" delta modifiers (`temperature_delta`, `rainfall_delta`, `soil_moisture_delta`) at the timeline projection endpoints, enabling cascading dynamic simulations on-the-fly without database mutations.
6. **Dynamic Dashboard Analytics & Rankings**: Real-time queries for top 5 hottest, wettest, or driest districts in India, filterable by country or specific states (e.g. Rajasthan, Uttar Pradesh).
7. **High-Performance API**: Fully asynchronous FastAPI endpoint connected to a Supabase PostgreSQL database via SQLAlchemy 2.0.

---

## 🏗️ Clean Architecture & Design Decisions

To maximize maintainability and production readiness, the repository follows a strict separation of concerns between **Machine Learning Research** and **Backend Inference Services**.

### 1. Separation of ML Research vs. Production Backend
- **`ml_research/`**: Contains all offline experimentation, feature engineering (`engineer_rainfall_features.py`, `engineer_drought_features.py`), model training, hyperparameter tuning, and raw dataset storage. This ensures the production backend is not bloated with heavy training libraries or experimental code.
- **`app/ml_services/`**: The online inference layer. It houses productionized predictor classes (e.g., `RainfallPredictor`) and serialized model weights (`.pkl`). These classes guarantee that the exact feature engineering logic used during training is recreated instantly during API requests.

### 2. Scientific Feature Engineering
We avoid arbitrary thresholds. Our intelligence systems are built on climate science:
- **Climate Zone Awareness**: India has diverse climates (Thar Desert vs. North-East). We use city-level and climate-zone percentiles to ensure drought in Rajasthan is evaluated differently than drought in Meghalaya.
- **Strict Leakage Prevention**: Chronological dataset splitting (Train ≤2020, Val 2021-22, Test ≥2023) is enforced to ensure no future data leaks into the training matrix.
- **Composite Scoring**: The Drought CDSS combines Rainfall SPI, Soil Moisture Anomalies, Temperature Stress, and Hydrological Stress into a single robust metric.

### 3. Asynchronous Backend Architecture
- **FastAPI + SQLAlchemy 2.0**: The entire request lifecycle is async, allowing the system to handle thousands of concurrent climate simulations without blocking.
- **Supabase PostgreSQL**: Managed database with connection pooling enabled.

---

## 🤖 Machine Learning Models in Detail

The Digital Twin is powered by a suite of interdependent models. They are trained on **ERA5-Land**, a state-of-the-art reanalysis dataset from the Copernicus Climate Data Store, which provides monthly resolutions of surface variables across decades.

### 1. Temperature Prediction Model
- **Goal**: Predict the localized surface temperature (`temperature_c`) for future dates.
- **Algorithm**: LightGBM / XGBoost Regressor
- **Dataset**: `temperature_training_dataset.csv`
- **Features Used**: Geography (Lat/Lon, Climate Zone), Temporal Sine/Cosine encodings, historical rolling averages (3-month, 6-month), and previous month lags.
- **How it Works**: The model learns thermal momentum and seasonal variations. By feeding it historical trajectories, it accurately forecasts future spikes or drops in temperature.
- **Validation**: Strict chronological split (Train: <2020, Val: 2021-22, Test: 2023+).

### 2. Rainfall & Monsoon Intelligence Model
- **Goal**: Predict raw `rainfall_mm` and classify the performance of the monsoon.
- **Algorithm**: LightGBM Regressor
- **Dataset**: `rainfall_training_dataset.csv`
- **Features Used**: **62 engineered features** including `rainfall_acceleration`, `evabs` (evaporation), `sro` (surface runoff), `soil_moisture`, and IMD 6-Phase Monsoon Encodings (pre-monsoon, active monsoon, post-monsoon).
- **How it Works**: Rainfall is notoriously difficult due to extreme variance (dry winters vs. torrential monsoons). The model uses hydrological relationships (soil moisture and evaporation) as leading indicators. The inference layer then calculates the ratio of predicted rainfall to the historical baseline to classify the season as a **Weak, Normal, or Strong Monsoon**.

### 3. Drought Intelligence Layer
- **Goal**: Predict the Drought Category (Low, Medium, High, Extreme) and output a continuous Drought Severity Score.
- **Algorithm**: Multi-class Classifier & Regressor (LightGBM)
- **Features Used**: Standardized Precipitation Index (SPI), Water Balance (Rainfall minus Evaporation and Runoff), Compound Stress (`moisture_stress`, `evaporation_stress`), and Persistence streaks.
- **How it Works**: Weighting rainfall deficits alongside soil moisture and heat stress to construct a Composite Drought Severity Score (CDSS). Evaluates drought using localized percentiles so Rajasthan and Himalayas are compared relative to their own climates. Outputs hydrological water intelligence and crop agricultural stress index.

### 4. Extreme Weather Subsystem
- **Goal**: Predict heatwave and extreme rainfall categories (Low, Medium, High, Extreme) and continuous severity indices (0 to 100).
- **Algorithm**: Chained Classifiers and Regressors (XGBoost & LightGBM)
- **Features Used**: Apparent temperature, temperature anomaly/z-score, antecedent soil moisture, extreme precipitation index, runoff pressure, and drainage overload proxies.
- **How it Works**: Performs heatwave and extreme rainfall classifications. Aggregates combined risk scores, compound event penalties, and generates actionable public safety advisories (e.g., flash flood evacuation notices).

---

## 📂 Folder Structure

```
backend/
├── app/                        # ⚡ PRODUCTION FASTAPI BACKEND
│   ├── main.py                 # Application entrypoint
│   ├── core/                   # Config and Database engine setup
│   ├── ml_services/            # 🧠 INFERENCE LAYER (Isolated ML predictions)
│   │   ├── models/             # Serialized .pkl weights and metrics
│   │   ├── predict_temperature.py
│   │   ├── predict_rainfall.py
│   │   ├── predict_drought.py
│   │   └── predict_extreme_weather.py # Inference classes with scenario simulation support
│   ├── models/                 # SQLAlchemy database models
│   ├── schemas/                # Pydantic v2 validation models
│   ├── routers/                # API route definitions
│   └── services/               # Database business logic
├── ml_research/                # 🔬 ML EXPERIMENTATION & TRAINING PIPELINE
│   ├── data/                   # Raw and processed datasets (ERA5)
│   ├── reports/                # Automated markdown reports for model diagnostics
│   └── scripts/                # Feature engineering and training scripts
│       ├── engineer_rainfall_features.py
│       ├── engineer_drought_features.py
│       ├── train_temperature.py
│       └── train_rainfall.py
├── alembic/                    # Database migrations
├── requirements.txt            # Package dependencies
└── .env.example                # Environment variable templates
```

---

## 🔄 ML Pipeline Overview

Our machine learning pipeline is robust and highly reproducible:

```mermaid
flowchart LR
    1[Data Ingestion (ERA5)] --> 2[Feature Engineering & Zone Encoding] --> 3[Chronological Splitting] --> 4[Auto Model Selection] --> 5[Hyperparameter Tuning] --> 6[Inference Serialization]
```

1. **Feature Engineering**: Scripts read base datasets and engineer complex rolling, lag, momentum, and climatology features.
2. **Auto Model Selection**: The training scripts automatically race algorithms (LightGBM, XGBoost, RandomForest, ExtraTrees) against a validation set and select the winner based on R² and RMSE.
3. **Inference Serialization**: The winning model, its hyperparameters, feature importance, and validation metrics (used for confidence scoring) are saved directly into `app/ml_services/models/`.

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.12+
- Access to a Supabase PostgreSQL instance.

### 2. Local Setup
1. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/Scripts/activate  # Windows (CMD/PowerShell)
   # OR
   source venv/bin/activate      # macOS/Linux
   ```

2. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables:**
   Copy `.env.example` to `.env` and configure your database parameters:
   ```bash
   cp .env.example .env
   ```

---

## 🗄️ Database Migrations (Alembic)

When you update or add any model in `app/models/`, generate and apply migrations:
```bash
alembic revision --autogenerate -m "Update schema"
alembic upgrade head
```

---

## 🗄️ Database Seeding

Before running the server, seed the database with the unique districts and historical records:
```bash
python seed_database.py
```

---

## 🏃‍♂️ Running the Server

Start the local development server with Uvicorn:
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- **API Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) (Swagger UI)
- **Health Check Endpoint**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## 🔬 Testing & Verification Suites

We provide automated test scripts to verify each ML integration subsystem. Run them from the project root:
- **Projections & Rankings Suite**:
  ```bash
  venv\Scripts\python.exe ml_research\scripts\verify_projections_and_rankings.py
  ```
- **Drought Layer Suite**:
  ```bash
  venv\Scripts\python.exe ml_research\scripts\verify_drought_intelligence.py
  ```
- **Extreme Weather Suite**:
  ```bash
  venv\Scripts\python.exe ml_research\scripts\verify_extreme_weather_intelligence.py
  ```
- **Base ML Predictors Suite**:
  ```bash
  venv\Scripts\python.exe ml_research\scripts\verify_gap4_integration.py
  ```

