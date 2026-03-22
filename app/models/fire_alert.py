"""Fire alert ORM model."""

import uuid
from datetime import datetime, timezone

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FireAlert(Base):
    """Persisted NASA FIRMS fire alert."""

    __tablename__ = "fire_alerts"
    __table_args__ = (
        UniqueConstraint(
            "latitude",
            "longitude",
            "acq_datetime",
            name="uq_fire_alerts_lat_lon_acq_datetime",
        ),
        Index("ix_fire_alerts_acq_datetime", "acq_datetime"),
        Index("ix_fire_alerts_geom", "geom", postgresql_using="gist"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    brightness: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[str] = mapped_column(String(16), nullable=False)
    acq_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    geom = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )
