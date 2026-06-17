from datetime import date
from sqlalchemy import Float, Date, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

class Forecast(Base):
    __tablename__ = "forecasts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    district_id: Mapped[int] = mapped_column(ForeignKey("districts.id", ondelete="CASCADE"), nullable=False)
    predicted_rainfall: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_temperature: Mapped[float] = mapped_column(Float, nullable=False)
    forecast_date: Mapped[date] = mapped_column(Date, nullable=False)

    district: Mapped["District"] = relationship("District", back_populates="forecasts")

    __table_args__ = (
        Index("ix_forecasts_district_date", "district_id", "forecast_date"),
    )
