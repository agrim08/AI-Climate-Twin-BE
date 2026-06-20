from datetime import date
from sqlalchemy import Float, Date, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

class ClimateObservation(Base):
    __tablename__ = "climate_observations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    district_id: Mapped[int] = mapped_column(ForeignKey("districts.id", ondelete="CASCADE"), nullable=False)
    rainfall: Mapped[float] = mapped_column(Float, nullable=False)
    temperature: Mapped[float] = mapped_column(Float, nullable=False)
    humidity: Mapped[float] = mapped_column(Float, nullable=False)
    observation_date: Mapped[date] = mapped_column(Date, nullable=False)

    district: Mapped["District"] = relationship("District", back_populates="observations")

    __table_args__ = (
        Index("ix_climate_obs_district_date", "district_id", "observation_date"),
    )
