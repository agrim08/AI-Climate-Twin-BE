from sqlalchemy import String, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

class District(Base):
    __tablename__ = "districts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    state: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    district_name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    observations: Mapped[list["ClimateObservation"]] = relationship(
        "ClimateObservation", back_populates="district", cascade="all, delete-orphan"
    )
    forecasts: Mapped[list["Forecast"]] = relationship(
        "Forecast", back_populates="district", cascade="all, delete-orphan"
    )
    simulation_results: Mapped[list["SimulationResult"]] = relationship(
        "SimulationResult", back_populates="district", cascade="all, delete-orphan"
    )
