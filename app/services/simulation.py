import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.simulation import SimulationResult
from app.schemas.simulation import SimulationResultCreate, SimulationResultUpdate

class SimulationResultService:
    @staticmethod
    async def get_simulation_results(db: AsyncSession, skip: int = 0, limit: int = 100):
        query = select(SimulationResult).offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_simulation_result_by_id(db: AsyncSession, sim_id: int):
        query = select(SimulationResult).where(SimulationResult.id == sim_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_simulation_results_by_user(db: AsyncSession, user_id: uuid.UUID, skip: int = 0, limit: int = 100):
        query = select(SimulationResult).where(SimulationResult.user_id == user_id).offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def create_simulation_result(db: AsyncSession, sim_in: SimulationResultCreate):
        db_sim = SimulationResult(
            user_id=sim_in.user_id,
            district_id=sim_in.district_id,
            rainfall_change=sim_in.rainfall_change,
            temperature_change=sim_in.temperature_change,
            humidity_change=sim_in.humidity_change,
            result_json=sim_in.result_json
        )
        db.add(db_sim)
        await db.commit()
        await db.refresh(db_sim)
        return db_sim

    @staticmethod
    async def update_simulation_result(db: AsyncSession, sim_id: int, sim_in: SimulationResultUpdate):
        db_sim = await SimulationResultService.get_simulation_result_by_id(db, sim_id)
        if not db_sim:
            return None
        update_data = sim_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_sim, key, value)
        await db.commit()
        await db.refresh(db_sim)
        return db_sim

    @staticmethod
    async def delete_simulation_result(db: AsyncSession, sim_id: int):
        db_sim = await SimulationResultService.get_simulation_result_by_id(db, sim_id)
        if not db_sim:
            return None
        await db.delete(db_sim)
        await db.commit()
        return db_sim

    @staticmethod
    async def run_simulation(
        db: AsyncSession,
        user_id: uuid.UUID,
        district_id: int,
        rainfall_change: float,
        temperature_change: float,
        humidity_change: float
    ):
        """
        Runs a climate simulation for a district by applying delta changes (anomalies) to the baseline climate summary.
        """
        # 1. Verify district exists
        from app.services.district import DistrictService
        district = await DistrictService.get_district_by_id(db, district_id)
        if not district:
            raise ValueError(f"District with ID {district_id} not found.")

        # 2. Fetch baseline climate data
        from app.services.analytics import AnalyticsService
        baseline = await AnalyticsService.get_district_summary(db, district_id)
        
        if not baseline:
            # Fallback baseline values if no observations exist yet
            base_temp = 27.0
            base_rain = 1200.0
            base_hum = 60.0
            obs_count = 0
        else:
            base_temp = baseline["average_temperature"]
            base_rain = baseline["average_rainfall"]
            base_hum = baseline["average_humidity"]
            obs_count = baseline["observation_count"]

        # 2. Compute projections:
        # Rainfall and humidity changes are percentage-based; temperature change is absolute.
        simulated_temp = round(base_temp + temperature_change, 2)
        simulated_rain = round(max(0.0, base_rain * (1 + rainfall_change / 100.0)), 2)
        simulated_hum = round(max(0.0, min(100.0, base_hum * (1 + humidity_change / 100.0))), 2)

        # 3. Categorize climate impact metrics
        drought_risk = "High" if simulated_rain < 600 and simulated_temp > 31.0 else "Moderate" if simulated_rain < 900 else "Low"
        flood_risk = "High" if simulated_rain > 2000 or (simulated_rain > 1600 and humidity_change > 15) else "Low"
        comfort_index = "Uncomfortable" if simulated_temp > 32.0 and simulated_hum > 70.0 else "Pleasant" if 20.0 <= simulated_temp <= 26.0 else "Moderate"

        result_json = {
            "baseline": {
                "temperature": base_temp,
                "rainfall": base_rain,
                "humidity": base_hum,
                "observation_count": obs_count
            },
            "projections": {
                "temperature": simulated_temp,
                "rainfall": simulated_rain,
                "humidity": simulated_hum
            },
            "impacts": {
                "drought_risk": drought_risk,
                "flood_risk": flood_risk,
                "comfort_index": comfort_index
            }
        }

        # 4. Save and return simulation record
        db_sim = SimulationResult(
            user_id=user_id,
            district_id=district_id,
            rainfall_change=rainfall_change,
            temperature_change=temperature_change,
            humidity_change=humidity_change,
            result_json=result_json
        )
        db.add(db_sim)
        await db.commit()
        await db.refresh(db_sim)
        return db_sim

    @staticmethod
    async def run_scenario_simulation(
        db: AsyncSession,
        user_id: uuid.UUID,
        district_id: int,
        scenario: str
    ):
        """
        Runs a climate simulation for a district using pre-defined scenarios.
        """
        scenario_lower = scenario.lower()
        if scenario_lower == "temperature_plus_1":
            temp_change = 1.0
            rain_change = 0.0
            hum_change = 0.0
        elif scenario_lower == "temperature_plus_2":
            temp_change = 2.0
            rain_change = 0.0
            hum_change = 0.0
        elif scenario_lower == "rainfall_minus_10":
            temp_change = 0.0
            rain_change = -10.0
            hum_change = 0.0
        elif scenario_lower == "rainfall_plus_10":
            temp_change = 0.0
            rain_change = 10.0
            hum_change = 0.0
        else:
            raise ValueError(
                f"Invalid scenario: {scenario}. Choose from: "
                "temperature_plus_1, temperature_plus_2, rainfall_minus_10, rainfall_plus_10"
            )

        return await SimulationResultService.run_simulation(
            db=db,
            user_id=user_id,
            district_id=district_id,
            rainfall_change=rain_change,
            temperature_change=temp_change,
            humidity_change=hum_change
        )

