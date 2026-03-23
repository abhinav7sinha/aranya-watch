"""Preview-mode fire alert data for local UI inspection."""

from __future__ import annotations

from math import atan2, cos, radians, sin, sqrt
from uuid import UUID

from app.models.schemas import FireAlertRead


PREVIEW_ALERTS: list[FireAlertRead] = [
    FireAlertRead.model_validate(
        {
            "id": UUID("11111111-1111-1111-1111-111111111111"),
            "latitude": 21.1458,
            "longitude": 79.0882,
            "brightness": 367.4,
            "confidence": "high",
            "acq_datetime": "2026-03-22T15:05:00Z",
            "created_at": "2026-03-22T15:08:00Z",
            "risk_score": 80.22,
        }
    ),
    FireAlertRead.model_validate(
        {
            "id": UUID("22222222-2222-2222-2222-222222222222"),
            "latitude": 18.5204,
            "longitude": 73.8567,
            "brightness": 341.7,
            "confidence": "nominal",
            "acq_datetime": "2026-03-22T14:20:00Z",
            "created_at": "2026-03-22T14:22:00Z",
            "risk_score": 52.51,
        }
    ),
    FireAlertRead.model_validate(
        {
            "id": UUID("33333333-3333-3333-3333-333333333333"),
            "latitude": 26.8467,
            "longitude": 80.9462,
            "brightness": 355.0,
            "confidence": "high",
            "acq_datetime": "2026-03-22T13:45:00Z",
            "created_at": "2026-03-22T13:46:00Z",
            "risk_score": 76.5,
        }
    ),
    FireAlertRead.model_validate(
        {
            "id": UUID("44444444-4444-4444-4444-444444444444"),
            "latitude": 23.2599,
            "longitude": 77.4126,
            "brightness": 318.9,
            "confidence": "low",
            "acq_datetime": "2026-03-22T12:10:00Z",
            "created_at": "2026-03-22T12:11:00Z",
            "risk_score": 25.67,
        }
    ),
    FireAlertRead.model_validate(
        {
            "id": UUID("55555555-5555-5555-5555-555555555555"),
            "latitude": 15.9129,
            "longitude": 79.7400,
            "brightness": 389.2,
            "confidence": "high",
            "acq_datetime": "2026-03-22T11:50:00Z",
            "created_at": "2026-03-22T11:52:00Z",
            "risk_score": 86.76,
        }
    ),
    FireAlertRead.model_validate(
        {
            "id": UUID("66666666-6666-6666-6666-666666666666"),
            "latitude": 11.1271,
            "longitude": 78.6569,
            "brightness": 332.8,
            "confidence": "nominal",
            "acq_datetime": "2026-03-22T11:12:00Z",
            "created_at": "2026-03-22T11:15:00Z",
            "risk_score": 49.84,
        }
    ),
]


def get_recent_preview_alerts(limit: int) -> list[FireAlertRead]:
    """Return preview alerts sorted by acquisition time."""

    alerts = sorted(PREVIEW_ALERTS, key=lambda alert: alert.acq_datetime, reverse=True)
    return alerts[:limit]


def get_preview_alerts_in_bbox(
    min_lat: float,
    max_lat: float,
    min_lon: float,
    max_lon: float,
) -> list[FireAlertRead]:
    """Return preview alerts within a bounding box."""

    return [
        alert
        for alert in PREVIEW_ALERTS
        if min_lat <= alert.latitude <= max_lat and min_lon <= alert.longitude <= max_lon
    ]


def get_preview_alerts_within_radius(lat: float, lon: float, radius_km: float) -> list[FireAlertRead]:
    """Return preview alerts within a radius using a haversine approximation."""

    return [
        alert
        for alert in PREVIEW_ALERTS
        if haversine_km(lat, lon, alert.latitude, alert.longitude) <= radius_km
    ]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute the great-circle distance between two points in kilometers."""

    earth_radius_km = 6371.0
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    origin_lat = radians(lat1)
    target_lat = radians(lat2)
    a = sin(d_lat / 2) ** 2 + cos(origin_lat) * cos(target_lat) * sin(d_lon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return earth_radius_km * c
