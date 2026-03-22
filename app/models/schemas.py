"""Pydantic schemas for API responses and ingestion records."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.services.risk import calculate_risk_score


class FireAlertBase(BaseModel):
    """Shared fire alert attributes."""

    latitude: float
    longitude: float
    brightness: float
    confidence: str
    acq_datetime: datetime


class FireAlertRead(FireAlertBase):
    """API representation for a fire alert."""

    id: UUID
    created_at: datetime
    risk_score: float

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_with_risk(cls, alert: object) -> "FireAlertRead":
        """Build a schema object and attach a computed risk score."""

        return cls.model_validate(
            {
                "id": getattr(alert, "id"),
                "latitude": getattr(alert, "latitude"),
                "longitude": getattr(alert, "longitude"),
                "brightness": getattr(alert, "brightness"),
                "confidence": getattr(alert, "confidence"),
                "acq_datetime": getattr(alert, "acq_datetime"),
                "created_at": getattr(alert, "created_at"),
                "risk_score": calculate_risk_score(
                    brightness=getattr(alert, "brightness"),
                    confidence=getattr(alert, "confidence"),
                ),
            }
        )


class FireAlertIngest(FireAlertBase):
    """Normalized fire alert payload used during ingestion."""
