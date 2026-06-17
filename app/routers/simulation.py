import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from pydantic import BaseModel
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.schemas.simulation import SimulationResult, SimulationResultCreate, SimulationResultUpdate
from app.services.simulation import SimulationResultService

router = APIRouter(prefix="/simulations", tags=["Simulation Results"])

class SimulationRunInput(BaseModel):
    district_id: int
    rainfall_change: float = 0.0  # percentage change
    temperature_change: float = 0.0  # absolute change in C
    humidity_change: float = 0.0  # percentage change

@router.post("/run", response_model=SimulationResult, status_code=status.HTTP_201_CREATED)
async def run_climate_simulation(
    sim_in: SimulationRunInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Run a new climate simulation for a specific district based on delta changes.
    Requires bearer token authentication.
    """
    return await SimulationResultService.run_simulation(
        db=db,
        user_id=current_user.id,
        district_id=sim_in.district_id,
        rainfall_change=sim_in.rainfall_change,
        temperature_change=sim_in.temperature_change,
        humidity_change=sim_in.humidity_change
    )

@router.get("/", response_model=List[SimulationResult])
async def read_simulation_results(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    return await SimulationResultService.get_simulation_results(db, skip=skip, limit=limit)

@router.get("/{sim_id}", response_model=SimulationResult)
async def read_simulation_result(sim_id: int, db: AsyncSession = Depends(get_db)):
    sim = await SimulationResultService.get_simulation_result_by_id(db, sim_id)
    if not sim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation result with ID {sim_id} not found"
        )
    return sim

@router.get("/user/{user_id}", response_model=List[SimulationResult])
async def read_user_simulation_results(
    user_id: uuid.UUID, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
):
    return await SimulationResultService.get_simulation_results_by_user(db, user_id, skip=skip, limit=limit)

@router.post("/", response_model=SimulationResult, status_code=status.HTTP_201_CREATED)
async def create_simulation_result(sim_in: SimulationResultCreate, db: AsyncSession = Depends(get_db)):
    return await SimulationResultService.create_simulation_result(db, sim_in)

@router.put("/{sim_id}", response_model=SimulationResult)
async def update_simulation_result(
    sim_id: int, sim_in: SimulationResultUpdate, db: AsyncSession = Depends(get_db)
):
    sim = await SimulationResultService.update_simulation_result(db, sim_id, sim_in)
    if not sim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation result with ID {sim_id} not found"
        )
    return sim

@router.delete("/{sim_id}", response_model=SimulationResult)
async def delete_simulation_result(sim_id: int, db: AsyncSession = Depends(get_db)):
    sim = await SimulationResultService.delete_simulation_result(db, sim_id)
    if not sim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation result with ID {sim_id} not found"
        )
    return sim
