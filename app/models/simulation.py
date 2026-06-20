import uuid
from datetime import datetime
from sqlalchemy import Float, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

class SimulationResult(Base):
    __tablename__ = "simulation_results"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    district_id: Mapped[int] = mapped_column(ForeignKey("districts.id", ondelete="CASCADE"), nullable=False)
    rainfall_change: Mapped[float] = mapped_column(Float, nullable=False)
    temperature_change: Mapped[float] = mapped_column(Float, nullable=False)
    humidity_change: Mapped[float] = mapped_column(Float, nullable=False)
    result_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="simulation_results")
    district: Mapped["District"] = relationship("District", back_populates="simulation_results")

    __table_args__ = (
        Index("ix_sim_results_user_id", "user_id"),
        Index("ix_sim_results_district_id", "district_id"),
    )
