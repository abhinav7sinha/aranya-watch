"""Database queries for fire alerts."""

from geoalchemy2 import Geography
from sqlalchemy import Select, cast, func, select
from sqlalchemy.orm import Session

from app.models.fire_alert import FireAlert


def get_recent_alerts(session: Session, limit: int) -> list[FireAlert]:
    """Return the most recent fire alerts."""

    statement: Select[tuple[FireAlert]] = (
        select(FireAlert).order_by(FireAlert.acq_datetime.desc()).limit(limit)
    )
    return list(session.scalars(statement).all())


def get_alerts_in_bbox(
    session: Session,
    min_lat: float,
    max_lat: float,
    min_lon: float,
    max_lon: float,
) -> list[FireAlert]:
    """Return alerts contained within a bounding box."""

    envelope = func.ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326)
    statement: Select[tuple[FireAlert]] = select(FireAlert).where(
        func.ST_Within(FireAlert.geom, envelope)
    )
    return list(session.scalars(statement).all())


def get_alerts_within_radius(
    session: Session,
    lat: float,
    lon: float,
    radius_km: float,
) -> list[FireAlert]:
    """Return alerts within a radius in kilometers."""

    radius_meters = radius_km * 1000
    center = func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326)
    statement: Select[tuple[FireAlert]] = select(FireAlert).where(
        func.ST_DWithin(
            cast(FireAlert.geom, Geography),
            cast(center, Geography),
            radius_meters,
        )
    )
    return list(session.scalars(statement).all())
